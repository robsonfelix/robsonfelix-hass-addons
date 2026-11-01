export TERM=xterm-256color
export LANG=C.UTF-8
PS1='\[\033[1;36m\]claude-code\[\033[0m\]:\[\033[1;34m\]\w\[\033[0m\]\$ '

# There used to be an update_mcp_token() here that wrote $SUPERVISOR_TOKEN into
# settings.json on every `c`/`cc`. It persisted the token to /homeassistant/,
# which ships inside every HA backup - and hass-mcp never read it (it reads
# HA_TOKEN from the environment, which the add-on exports). Removed.

# Aliases
alias ll='ls -la'
alias c='claude $CLAUDE_FLAGS'
alias cc='claude --continue $CLAUDE_FLAGS'
alias ha-config='cd /homeassistant'
alias ha-logs='cat /homeassistant/home-assistant.log 2>/dev/null || echo "Log not found"'
