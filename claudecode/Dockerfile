ARG BUILD_FROM

# Build a current ttyd web client: the one embedded in the ttyd 1.7.7 binary
# predates OSC 52 clipboard support, so startup serves this build via --index.
# Built with yarn so ttyd's lockfile is honored (npm resolves newer transitive
# deps and fails type-checking). Everything is pinned - ttyd commit, corepack,
# lockfile deps - so the output is reproducible. COREPACK_INTEGRITY_KEYS=0
# keeps the pinned corepack working across npm signing-key rotations;
# integrity comes from the yarn.lock checksums. Drop this stage and the
# --index flag once a ttyd release newer than 1.7.7 ships.
FROM ${BUILD_FROM} AS ttyd-client
RUN apk add --no-cache curl nodejs npm
ARG TTYD_CLIENT_COMMIT=2922cb89f518bae4d0fcf4d757a7419638fc71fc
RUN curl -fsSL --retry 5 --retry-delay 2 --retry-all-errors \
        "https://github.com/tsl0922/ttyd/archive/${TTYD_CLIENT_COMMIT}.tar.gz" \
        | tar xz && mv "ttyd-${TTYD_CLIENT_COMMIT}" /ttyd
WORKDIR /ttyd/html
ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
    COREPACK_NPM_REGISTRY=https://registry.npmjs.org \
    COREPACK_INTEGRITY_KEYS=0
RUN npm install -g corepack@0.35.0 && corepack enable && \
    yarn install --immutable && yarn run inline

FROM ${BUILD_FROM}

# Labels
LABEL maintainer="Robson Felix"
LABEL org.opencontainers.image.title="Claude Code for Home Assistant"
LABEL org.opencontainers.image.description="Claude Code CLI with web terminal and HA integration"
LABEL org.opencontainers.image.source="https://github.com/robsonfelix/robsonfelix-hass-addons"
LABEL org.opencontainers.image.licenses="MIT"

# Environment setup
ENV \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    TERM=xterm-256color

# Install system dependencies (ttyd installed separately as static binary)
RUN apk add --no-cache \
    bash \
    curl \
    git \
    github-cli \
    jq \
    nodejs \
    npm \
    openssh-client \
    libstdc++ \
    ncurses \
    vim \
    nano \
    tmux \
    coreutils \
    findutils \
    grep \
    sed \
    gawk \
    ca-certificates \
    openssl \
    ripgrep \
    p7zip \
    socat \
    docker-cli \
    && update-ca-certificates

# Install ttyd static binary (avoids libwebsockets issues); the web client
# it serves comes from the ttyd-client build stage above (see --index).
ARG BUILD_ARCH
RUN case "${BUILD_ARCH}" in \
        amd64) TTYD_ARCH="x86_64" ;; \
        aarch64) TTYD_ARCH="aarch64" ;; \
        armv7|armhf) TTYD_ARCH="armhf" ;; \
        i386) TTYD_ARCH="i686" ;; \
        *) TTYD_ARCH="x86_64" ;; \
    esac && \
    curl -fsSL --retry 5 --retry-delay 2 --retry-all-errors \
        "https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.${TTYD_ARCH}" -o /usr/bin/ttyd && \
    chmod +x /usr/bin/ttyd
COPY --from=ttyd-client /ttyd/html/dist/inline.html /usr/share/ttyd/index.html

# Install Claude Code.
# 2.1.113 replaced the JS entrypoint with a Bun-compiled native binary, whose
# JavaScriptCore requires AVX. Hosts that lack it - notably VMs exposing the
# generic kvm64 CPU model - cannot run 2.1.113+ (it deadlocks or dies with
# SIGILL). Fix that at the hypervisor (Proxmox CPU type "host"), not here.
# No version is hardcoded: take latest when it runs, otherwise the newest
# release that passes a smoke test, so the add-on still builds on such hosts.
COPY install-claude.sh /usr/local/bin/install-claude.sh
RUN chmod +x /usr/local/bin/install-claude.sh && /usr/local/bin/install-claude.sh

# Install hass-mcp for Home Assistant integration and pymodbus for Modbus operations
RUN pip3 install --no-cache-dir --break-system-packages hass-mcp pymodbus pyserial

# Install mbpoll (Modbus command line tool) from source
RUN apk add --no-cache --virtual .build-deps \
    build-base \
    cmake \
    libmodbus-dev \
    && git clone https://github.com/epsilonrt/mbpoll.git /tmp/mbpoll \
    && cd /tmp/mbpoll \
    && mkdir build && cd build \
    && cmake .. \
    && make \
    && make install \
    && cd / \
    && rm -rf /tmp/mbpoll \
    && apk del .build-deps \
    && apk add --no-cache libmodbus

# Pre-cache Playwright MCP server (npx cache avoids /usr/local/bin/mcp conflict with hass-mcp)
ENV NPM_CONFIG_CACHE=/root/.npm
RUN npx @playwright/mcp --version || true

# Install Home Assistant CLI (ha command)
# Pinned and retried: a transient DNS failure used to abort the whole build
# (curl exit 6). Upstream publishes only amd64 and aarch64, so other arches skip
# the CLI with a warning instead of failing the build on a 404.
ARG HA_CLI_VERSION=5.2.0
RUN case "${BUILD_ARCH}" in \
        amd64|aarch64) \
            curl -fsSL --retry 5 --retry-delay 2 --retry-all-errors \
                "https://github.com/home-assistant/cli/releases/download/${HA_CLI_VERSION}/ha_${BUILD_ARCH}" \
                -o /usr/local/bin/ha && \
            chmod +x /usr/local/bin/ha ;; \
        *) \
            echo "[WARN] Home Assistant CLI is not published for ${BUILD_ARCH}; the 'ha' command will be unavailable" ;; \
    esac

# Create necessary directories (NOT /root/.claude - will be symlinked at runtime)
RUN mkdir -p \
    /homeassistant \
    /root/.config \
    /root/.local/bin

# Shell and tmux config.
# These were heredocs (RUN cat > file << 'EOF'), which require BuildKit and a
# `# syntax=docker/dockerfile:1.4` directive. Builders without heredoc support
# parsed the body as Dockerfile instructions ("unknown instruction: set").
# COPY works on every builder and needs no syntax image.
COPY rootfs/root/.tmux.conf /root/.tmux.conf
COPY rootfs/root/.bashrc /root/.bashrc

# Ensure .bashrc is sourced for login shells too
RUN echo 'source ~/.bashrc' > /root/.profile

# Set up PATH
ENV PATH="/root/.local/bin:${PATH}"

# Set working directory
WORKDIR /homeassistant

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:7681/ || exit 1

# Startup script that reads config and persists Claude auth
# Use /homeassistant/.claudecode which is always persistent
ENTRYPOINT []
CMD ["/bin/bash", "-c", "\
  export HA_TOKEN=\"$SUPERVISOR_TOKEN\" && \
  export HA_URL=\"http://supervisor/core\" && \
  PERSIST_DIR=/homeassistant/.claudecode && \
  mkdir -p $PERSIST_DIR/config /root/.config && \
  printf '%s\n' \
    '# Claude Code - Home Assistant Add-on' \
    '' \
    '## Path Mapping' \
    '' \
    'In this add-on container, paths are mapped differently than HA Core:' \
    '- \\`/homeassistant\\` = HA config directory (equivalent to \\`/config\\` in HA Core)' \
    '- \\`/config\\` does NOT exist - always use \\`/homeassistant\\`' \
    '' \
    'When users mention \\`/config/...\\`, translate to \\`/homeassistant/...\\`' \
    '' \
    '## Available Paths' \
    '' \
    '| Path | Description | Access |' \
    '|------|-------------|--------|' \
    '| \\`/homeassistant\\` | HA configuration | read-write |' \
    '| \\`/share\\` | Shared folder | read-write |' \
    '| \\`/media\\` | Media files | read-write |' \
    '| \\`/ssl\\` | SSL certificates | read-only |' \
    '| \\`/backup\\` | Backups | read-only |' \
    '' \
    '## Home Assistant Integration' \
    '' \
    'Use the \\`homeassistant\\` MCP server to query entities and call services.' \
    '' \
    '## Reading Home Assistant Logs' \
    '' \
    '**Log levels (from most to least verbose):**' \
    '- \\`debug\\` - Only shown if explicitly enabled in configuration.yaml' \
    '- \\`info\\` - General information, shown by default' \
    '- \\`warning\\` - Warnings, always shown' \
    '- \\`error\\` - Errors, always shown' \
    '' \
    '**Commands to read logs:**' \
    '\\`\\`\\`bash' \
    '# View recent logs (ha CLI)' \
    'ha core logs 2>&1 | tail -100' \
    '' \
    '# Filter by keyword' \
    'ha core logs 2>&1 | grep -i keyword' \
    '' \
    '# Filter errors only' \
    'ha core logs 2>&1 | grep -iE \"(error|exception)\"' \
    '' \
    '# Alternative: read log file directly' \
    'tail -100 /homeassistant/home-assistant.log' \
    '\\`\\`\\`' \
    '' \
    '**To enable debug logging for an integration**, add to \\`configuration.yaml\\`:' \
    '\\`\\`\\`yaml' \
    'logger:' \
    '  default: info' \
    '  logs:' \
    '    custom_components.YOUR_INTEGRATION: debug' \
    '\\`\\`\\`' \
    '' \
    '**Key insight:** \\`_LOGGER.debug()\\` calls are invisible unless the logger level is set to debug. Use \\`_LOGGER.info()\\` or \\`_LOGGER.warning()\\` for logs that should always appear.' \
    > $PERSIST_DIR/CLAUDE.md && \
  if [ ! -L /root/.claude ]; then rm -rf /root/.claude; ln -s $PERSIST_DIR /root/.claude; fi && \
  if [ ! -L /root/.config/claude-code ]; then rm -rf /root/.config/claude-code; ln -s $PERSIST_DIR/config /root/.config/claude-code; fi && \
  if [ ! -L /root/.claude.json ]; then touch $PERSIST_DIR/.claude.json; rm -f /root/.claude.json; ln -s $PERSIST_DIR/.claude.json /root/.claude.json; fi && \
  FONT_SIZE=$(jq -r '.terminal_font_size // 14' /data/options.json) && \
  THEME=$(jq -r '.terminal_theme // \"dark\"' /data/options.json) && \
  SESSION_PERSIST=$(jq -r 'if .session_persistence == null then true else .session_persistence end' /data/options.json) && \
  ENABLE_MCP=$(jq -r 'if .enable_mcp == null then true else .enable_mcp end' /data/options.json) && \
  ENABLE_PLAYWRIGHT=$(jq -r '.enable_playwright_mcp // false' /data/options.json) && \
  PLAYWRIGHT_HOST=$(jq -r '.playwright_cdp_host // \"\"' /data/options.json) && \
  if [ -z \"$PLAYWRIGHT_HOST\" ] && [ \"$ENABLE_PLAYWRIGHT\" = \"true\" ]; then \
    echo '[INFO] Auto-detecting Playwright Browser hostname...' && \
    PLAYWRIGHT_HOST=$(curl -s -H \"Authorization: Bearer $SUPERVISOR_TOKEN\" http://supervisor/addons | jq -r '.data.addons[] | select(.slug | endswith(\"playwright-browser\") or endswith(\"_playwright-browser\")) | .hostname' | head -1) && \
    if [ -n \"$PLAYWRIGHT_HOST\" ] && [ \"$PLAYWRIGHT_HOST\" != \"null\" ]; then \
      echo \"[INFO] Found Playwright Browser: $PLAYWRIGHT_HOST\"; \
    else \
      echo '[WARN] Playwright Browser add-on not found, using default hostname'; \
      PLAYWRIGHT_HOST=\"playwright-browser\"; \
    fi; \
  fi && \
  REMOTE_CONTROL=$(jq -r '.enable_remote_control // false' /data/options.json) && \
  RC_SESSION_PREFIX=$(jq -r '.remote_control_session_prefix // \"HomeAssistant\"' /data/options.json) && \
  SETTINGS_FILE=/root/.claude/settings.json && \
  [ -f \"$SETTINGS_FILE\" ] || echo '{}' > \"$SETTINGS_FILE\" && \
  if jq -e '.mcpServers.homeassistant.env.HASS_TOKEN' \"$SETTINGS_FILE\" > /dev/null 2>&1; then \
    jq 'del(.mcpServers.homeassistant.env.HASS_TOKEN)' \"$SETTINGS_FILE\" > /tmp/settings.tmp && \
    mv /tmp/settings.tmp \"$SETTINGS_FILE\" && \
    echo '[INFO] Removed a Supervisor token that older versions persisted into settings.json'; \
    echo '[INFO] That file lives in your HA config dir and is included in backups'; \
  fi && \
  if ! grep -qw avx /proc/cpuinfo 2>/dev/null; then \
    echo '[WARN] This CPU does not expose AVX. Claude Code 2.1.113+ is a Bun-compiled'; \
    echo '[WARN] binary that requires it, so this add-on is running an older release.'; \
    echo '[WARN] On Proxmox set the VM CPU type to \"host\" (or x86-64-v3), then fully'; \
    echo '[WARN] stop and start the VM. Verify with: grep -o -m1 avx2 /proc/cpuinfo'; \
  fi && \
  BUILT_VERSION=$(cat /etc/claude-code-version 2>/dev/null || echo unknown) && \
  AUTO_UPDATE=$(jq -r '.auto_update_claude // false' /data/options.json) && \
  if [ \"$AUTO_UPDATE\" = \"true\" ]; then \
    echo \"[WARN] auto_update_claude=true; the build verified $BUILT_VERSION, an update may install a release that cannot run\" && \
    timeout 300 npm update -g @anthropic-ai/claude-code || echo '[WARN] Update failed; keeping the installed version'; \
    if ! timeout 30 claude --version < /dev/null > /dev/null 2>&1; then \
      echo \"[ERROR] The updated Claude Code does not run here; rolling back to $BUILT_VERSION\" && \
      timeout 300 npm install -g @anthropic-ai/claude-code@$BUILT_VERSION || echo '[ERROR] Rollback failed'; \
    fi; \
  else \
    echo \"[INFO] Claude Code $BUILT_VERSION (verified at build time)\"; \
  fi && \
  if timeout 30 claude --version < /dev/null > /dev/null 2>&1; then \
    CLAUDE_OK=true; \
  else \
    CLAUDE_OK=false; \
    echo '[ERROR] claude CLI did not respond within 30s - skipping MCP setup'; \
    echo '[ERROR] The terminal will still start so you can debug from inside the add-on'; \
  fi && \
  if [ \"$CLAUDE_OK\" = \"true\" ]; then \
    timeout 30 claude mcp remove homeassistant -s user > /dev/null 2>&1 || true; \
    timeout 30 claude mcp remove playwright -s user > /dev/null 2>&1 || true; \
  fi && \
  if [ \"$CLAUDE_OK\" = \"true\" ] && [ \"$ENABLE_MCP\" = \"true\" ]; then \
    timeout 30 claude mcp add-json homeassistant '{\"command\":\"hass-mcp\"}' -s user && \
    SETTINGS_FILE=/root/.claude/settings.json && \
    ALLOWED_TOOLS='[\"mcp__homeassistant__get_version\",\"mcp__homeassistant__get_entity\",\"mcp__homeassistant__list_entities\",\"mcp__homeassistant__search_entities_tool\",\"mcp__homeassistant__domain_summary_tool\",\"mcp__homeassistant__list_automations\",\"mcp__homeassistant__get_history\",\"mcp__homeassistant__get_error_log\",\"Read(/homeassistant/**)\",\"Read(/config/**)\",\"Read(/share/**)\",\"Read(/media/**)\",\"Glob(/homeassistant/**)\",\"Glob(/config/**)\",\"Grep(/homeassistant/**)\",\"Grep(/config/**)\"]' && \
    jq --argjson tools \"$ALLOWED_TOOLS\" '.permissions.allow = ($tools + (.permissions.allow // []) | unique)' $SETTINGS_FILE > /tmp/settings.tmp && mv /tmp/settings.tmp $SETTINGS_FILE && \
    echo '[INFO] MCP configured with Home Assistant integration'; \
    echo '[INFO] Pre-authorized read-only MCP tools'; \
  elif [ \"$ENABLE_MCP\" = \"true\" ]; then \
    echo '[WARN] MCP is enabled but was skipped: the claude CLI is not responding'; \
  else \
    echo '[INFO] MCP disabled'; \
  fi && \
  if [ \"$CLAUDE_OK\" = \"true\" ] && [ \"$ENABLE_PLAYWRIGHT\" = \"true\" ]; then \
    timeout 30 claude mcp add-json playwright \"{\\\"command\\\":\\\"npx\\\",\\\"args\\\":[\\\"--no-install\\\",\\\"@playwright/mcp\\\",\\\"--cdp-endpoint\\\",\\\"http://${PLAYWRIGHT_HOST}:9222\\\"]}\" -s user && \
    echo \"[INFO] Playwright MCP enabled (CDP: http://${PLAYWRIGHT_HOST}:9222)\"; \
    echo '[INFO] Make sure the Playwright Browser add-on is installed and running'; \
  elif [ \"$ENABLE_PLAYWRIGHT\" = \"true\" ]; then \
    echo '[WARN] Playwright MCP is enabled but was skipped: the claude CLI is not responding'; \
  else \
    echo '[INFO] Playwright MCP disabled'; \
  fi && \
  if [ \"$REMOTE_CONTROL\" = \"true\" ]; then \
    jq '.remoteControlAtStartup = true' \"$SETTINGS_FILE\" > /tmp/settings.tmp && mv /tmp/settings.tmp \"$SETTINGS_FILE\" && \
    echo '[INFO] Remote Control enabled - Claude Code will auto-start with remote control'; \
  else \
    jq 'del(.remoteControlAtStartup)' \"$SETTINGS_FILE\" > /tmp/settings.tmp && mv /tmp/settings.tmp \"$SETTINGS_FILE\"; \
    echo '[INFO] Remote Control auto-start disabled'; \
  fi && \
  if [ \"$THEME\" = \"dark\" ]; then \
    COLORS='background=#1e1e2e,foreground=#cdd6f4,cursor=#f5e0dc'; \
  else \
    COLORS='background=#eff1f5,foreground=#4c4f69,cursor=#dc8a78'; \
  fi && \
  if [ \"$SESSION_PERSIST\" = \"true\" ]; then \
    SHELL_CMD='tmux new-session -A -s claude'; \
  else \
    SHELL_CMD='bash --login'; \
  fi && \
  if [ \"$REMOTE_CONTROL\" = \"true\" ]; then export CLAUDE_REMOTE_CONTROL_SESSION_NAME_PREFIX=\"$RC_SESSION_PREFIX\"; fi && \
  cd /homeassistant && \
  exec ttyd --port 7681 --writable --ping-interval 30 --max-clients 5 \
    --index /usr/share/ttyd/index.html \
    -t fontSize=$FONT_SIZE \
    -t fontFamily=Monaco,Consolas,monospace \
    -t scrollback=20000 \
    -t \"theme=$COLORS\" \
    $SHELL_CMD \
"]
