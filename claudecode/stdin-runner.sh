#!/bin/bash
# Headless Claude Code runs triggered from Home Assistant automations.
#
# An automation calls the built-in hassio.addon_stdin service with a JSON
# payload, one object per line:
#
#   {"prompt": "...", "model": "sonnet", "run_id": "my-task"}
#   {"prompt_file": "/share/task.md", "allowed_tools": ["mcp__homeassistant__*"]}
#   {"abort": true}
#
# Task fields (one of prompt/prompt_file required): prompt, prompt_file,
# model, allowed_tools, run_id.
# Control messages: {"abort": true} hard-kills the currently running task.
#
# One task runs at a time; a task arriving while one is active is rejected
# with a claudecode_run_rejected event. Outcomes are reported as HA events
# claudecode_run_started / claudecode_run_finished (the latter carries
# aborted: true when the run was killed by an abort message).

OPTS=/data/options.json
DEFAULT_MODEL=$(jq -r '.default_task_model // ""' "$OPTS")
DEFAULT_TOOLS=$(jq -c '.default_task_allowed_tools // []' "$OPTS")
MAX_MINUTES=$(jq -r '.task_max_runtime_minutes // 30' "$OPTS")

LOG_DIR=/config/task-logs
mkdir -p "$LOG_DIR" 2>/dev/null || LOG_DIR=/homeassistant/.claudecode/task-logs
mkdir -p "$LOG_DIR"

RUN_DIR=/tmp/claudecode-task
mkdir -p "$RUN_DIR"

fire_event() {
    local event="$1" payload="$2"
    curl -s -m 10 -X POST \
        -H "Authorization: Bearer ${SUPERVISOR_TOKEN}" \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "http://supervisor/core/api/events/${event}" > /dev/null
}

run_active() {
    [ -n "$WATCHER_PID" ] && kill -0 "$WATCHER_PID" 2>/dev/null
}

WATCHER_PID=""

echo "[INFO] stdin task runner ready (default model: ${DEFAULT_MODEL:-claude default}, max ${MAX_MINUTES} min)"
fire_event claudecode_runner_ready "$(jq -n --arg m "${DEFAULT_MODEL:-default}" '{model: $m}')"

while IFS= read -r line; do
    [ -z "$line" ] && continue
    if ! jq -e . > /dev/null 2>&1 <<< "$line"; then
        echo "[WARN] task runner: ignoring non-JSON stdin line"
        continue
    fi

    # ---- control: abort --------------------------------------------------
    if [ "$(jq -r '.abort // false' <<< "$line")" = "true" ]; then
        if run_active; then
            echo "[INFO] task runner: aborting current run"
            touch "$RUN_DIR/aborted"
            PGID=$(cat "$RUN_DIR/pgid" 2>/dev/null)
            [ -n "$PGID" ] && kill -TERM -- "-$PGID" 2>/dev/null
            sleep 2
            [ -n "$PGID" ] && kill -KILL -- "-$PGID" 2>/dev/null
        else
            echo "[INFO] task runner: abort received but no run is active"
        fi
        continue
    fi

    # ---- task ------------------------------------------------------------
    RUN_ID=$(jq -r '.run_id // "task"' <<< "$line")
    if run_active; then
        echo "[WARN] task runner: busy - rejecting '$RUN_ID'"
        fire_event claudecode_run_rejected \
            "$(jq -n --arg id "$RUN_ID" '{run_id: $id, reason: "another run is active"}')"
        continue
    fi

    MODEL=$(jq -r '.model // empty' <<< "$line")
    [ -z "$MODEL" ] && MODEL="$DEFAULT_MODEL"
    TOOLS=$(jq -c 'if (.allowed_tools // []) | length > 0 then .allowed_tools else empty end' <<< "$line")
    [ -z "$TOOLS" ] && TOOLS="$DEFAULT_TOOLS"
    PROMPT=$(jq -r '.prompt // empty' <<< "$line")
    PROMPT_FILE=$(jq -r '.prompt_file // empty' <<< "$line")
    if [ -z "$PROMPT" ] && [ -n "$PROMPT_FILE" ] && [ -f "$PROMPT_FILE" ]; then
        PROMPT=$(cat "$PROMPT_FILE")
    fi
    if [ -z "$PROMPT" ]; then
        echo "[WARN] task runner: run '$RUN_ID' has no prompt/prompt_file - skipped"
        fire_event claudecode_run_finished \
            "$(jq -n --arg id "$RUN_ID" '{run_id: $id, success: false, error: "no prompt provided"}')"
        continue
    fi

    TS=$(date +%Y%m%d-%H%M%S)
    LOG_FILE="${LOG_DIR}/${RUN_ID}-${TS}.log"
    rm -f "$RUN_DIR/aborted" "$RUN_DIR/pgid"
    printf '%s' "$PROMPT" > "$RUN_DIR/prompt"
    echo "$MODEL" > "$RUN_DIR/model"
    echo "$TOOLS" > "$RUN_DIR/tools"

    echo "[INFO] task runner: starting '$RUN_ID' (model: ${MODEL:-default}, log: $LOG_FILE)"
    fire_event claudecode_run_started \
        "$(jq -n --arg id "$RUN_ID" --arg log "$LOG_FILE" '{run_id: $id, log_path: $log}')"

    (
        START=$(date +%s)
        setsid bash -c '
            echo $$ > '"$RUN_DIR"'/pgid
            ARGS=(-p "$(cat '"$RUN_DIR"'/prompt)")
            MODEL=$(cat '"$RUN_DIR"'/model)
            [ -n "$MODEL" ] && ARGS+=(--model "$MODEL")
            while IFS= read -r tool; do
                ARGS+=(--allowedTools "$tool")
            done < <(jq -r ".[]" '"$RUN_DIR"'/tools)
            exec timeout '"$((MAX_MINUTES * 60))"' claude "${ARGS[@]}"
        ' > "$LOG_FILE" 2>&1
        CODE=$?
        DURATION=$(( $(date +%s) - START ))
        ABORTED=false
        [ -f "$RUN_DIR/aborted" ] && ABORTED=true && rm -f "$RUN_DIR/aborted"
        SUCCESS=false
        [ "$CODE" -eq 0 ] && [ "$ABORTED" = "false" ] && SUCCESS=true
        TAIL=$(tail -c 400 "$LOG_FILE" 2>/dev/null)
        echo "[INFO] task runner: '$RUN_ID' finished (exit $CODE, aborted=$ABORTED, ${DURATION}s)"
        fire_event claudecode_run_finished \
            "$(jq -n --arg id "$RUN_ID" --arg log "$LOG_FILE" \
                  --argjson ok "$SUCCESS" --argjson code "$CODE" \
                  --argjson dur "$DURATION" --argjson ab "$ABORTED" \
                  --arg tail "$TAIL" \
                  '{run_id: $id, success: $ok, exit_code: $code, duration_seconds: $dur, aborted: $ab, log_path: $log, output_tail: $tail}')"
    ) &
    WATCHER_PID=$!
done
echo "[INFO] task runner: stdin closed, exiting"
