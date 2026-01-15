ARG BUILD_FROM
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
    && update-ca-certificates

# Install ttyd static binary (avoids libwebsockets issues)
ARG BUILD_ARCH
RUN case "${BUILD_ARCH}" in \
        amd64) TTYD_ARCH="x86_64" ;; \
        aarch64) TTYD_ARCH="aarch64" ;; \
        armv7|armhf) TTYD_ARCH="armhf" ;; \
        i386) TTYD_ARCH="i686" ;; \
        *) TTYD_ARCH="x86_64" ;; \
    esac && \
    curl -fsSL "https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.${TTYD_ARCH}" -o /usr/bin/ttyd && \
    chmod +x /usr/bin/ttyd

# Install Claude Code via npm
RUN npm install -g @anthropic-ai/claude-code

# Install hass-mcp for Home Assistant integration
RUN pip3 install --no-cache-dir --break-system-packages hass-mcp

# Install Playwright MCP server (official Microsoft package)
RUN npm install -g @playwright/mcp

# Install Home Assistant CLI (ha command)
RUN case "${BUILD_ARCH}" in \
        amd64) HA_ARCH="amd64" ;; \
        aarch64) HA_ARCH="aarch64" ;; \
        armv7|armhf) HA_ARCH="armhf" ;; \
        i386) HA_ARCH="i386" ;; \
        *) HA_ARCH="amd64" ;; \
    esac && \
    curl -fsSL "https://github.com/home-assistant/cli/releases/latest/download/ha_${HA_ARCH}" -o /usr/local/bin/ha && \
    chmod +x /usr/local/bin/ha

# Create necessary directories (NOT /root/.claude - will be symlinked at runtime)
RUN mkdir -p \
    /homeassistant \
    /root/.config \
    /root/.local/bin

# Configure tmux with large scrollback buffer and scroll support
RUN cat > /root/.tmux.conf << 'EOF'
set -g history-limit 20000
# Disable alternate screen buffer to allow terminal scrollback
set -ga terminal-overrides ',xterm*:smcup@:rmcup@'
# Enable mouse support for scrolling (but may affect copy/paste)
set -g mouse on
# Bind mouse wheel to scroll through history in copy mode
bind -n WheelUpPane if-shell -F -t = "#{mouse_any_flag}" "send-keys -M" "if -Ft= '#{pane_in_mode}' 'send-keys -M' 'select-pane -t=; copy-mode -e; send-keys -M'"
bind -n WheelDownPane select-pane -t= \; send-keys -M
EOF

# Configure bash with aliases and prompt
RUN cat > /root/.bashrc << 'EOF'
export TERM=xterm-256color
export LANG=C.UTF-8
PS1='\[\033[1;36m\]claude-code\[\033[0m\]:\[\033[1;34m\]\w\[\033[0m\]\$ '

# Aliases
alias ll='ls -la'
alias c='claude'
alias cc='claude --continue'
alias ha-config='cd /homeassistant'
alias ha-logs='cat /homeassistant/home-assistant.log 2>/dev/null || echo "Log not found"'
EOF

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
  SESSION_PERSIST=$(jq -r '.session_persistence // true' /data/options.json) && \
  ENABLE_MCP=$(jq -r '.enable_mcp // true' /data/options.json) && \
  ENABLE_PLAYWRIGHT=$(jq -r '.enable_playwright_mcp // false' /data/options.json) && \
  PLAYWRIGHT_HOST=$(jq -r '.playwright_cdp_host // \"\"' /data/options.json) && \
  if [ -z \"$PLAYWRIGHT_HOST\" ]; then PLAYWRIGHT_HOST=\"playwright-browser\"; fi && \
  AUTO_UPDATE=$(jq -r '.auto_update_claude // true' /data/options.json) && \
  if [ \"$AUTO_UPDATE\" = \"true\" ]; then \
    echo '[INFO] Checking for Claude Code updates...' && \
    npm update -g @anthropic-ai/claude-code 2>/dev/null || echo '[WARN] Update check failed, continuing...'; \
  fi && \
  claude mcp remove homeassistant -s user 2>/dev/null || true && \
  claude mcp remove playwright -s user 2>/dev/null || true && \
  if [ \"$ENABLE_MCP\" = \"true\" ]; then \
    claude mcp add-json homeassistant '{\"command\":\"hass-mcp\"}' -s user && \
    SETTINGS_FILE=/root/.claude/settings.json && \
    ALLOWED_TOOLS='[\"mcp__homeassistant__get_version\",\"mcp__homeassistant__get_entity\",\"mcp__homeassistant__list_entities\",\"mcp__homeassistant__search_entities_tool\",\"mcp__homeassistant__domain_summary_tool\",\"mcp__homeassistant__list_automations\",\"mcp__homeassistant__get_history\",\"mcp__homeassistant__get_error_log\",\"Read(/homeassistant/**)\",\"Read(/config/**)\",\"Read(/share/**)\",\"Read(/media/**)\",\"Glob(/homeassistant/**)\",\"Glob(/config/**)\",\"Grep(/homeassistant/**)\",\"Grep(/config/**)\"]' && \
    jq --argjson tools \"$ALLOWED_TOOLS\" '.permissions.allow = ($tools + (.permissions.allow // []) | unique)' $SETTINGS_FILE > /tmp/settings.tmp && mv /tmp/settings.tmp $SETTINGS_FILE && \
    echo '[INFO] MCP configured with Home Assistant integration'; \
    echo '[INFO] Pre-authorized read-only MCP tools'; \
  else \
    echo '[INFO] MCP disabled'; \
  fi && \
  if [ \"$ENABLE_PLAYWRIGHT\" = \"true\" ]; then \
    claude mcp add-json playwright \"{\\\"command\\\":\\\"npx\\\",\\\"args\\\":[\\\"-y\\\",\\\"@playwright/mcp\\\",\\\"--cdp-endpoint\\\",\\\"http://${PLAYWRIGHT_HOST}:9222\\\"]}\" -s user && \
    echo \"[INFO] Playwright MCP enabled (CDP: http://${PLAYWRIGHT_HOST}:9222)\"; \
    echo '[INFO] Make sure the Playwright Browser add-on is installed and running'; \
  else \
    echo '[INFO] Playwright MCP disabled'; \
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
  cd /homeassistant && \
  exec ttyd --port 7681 --writable --ping-interval 30 --max-clients 5 \
    -t fontSize=$FONT_SIZE \
    -t fontFamily=Monaco,Consolas,monospace \
    -t scrollback=20000 \
    -t \"theme=$COLORS\" \
    $SHELL_CMD \
"]
