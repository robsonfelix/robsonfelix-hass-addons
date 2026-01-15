# Changelog

All notable changes to this project will be documented in this file.

## [1.2.43] - 2026-01-14

### Changed
- Upgraded `hassio_role` from `homeassistant` to `manager`
- Enables access to other add-ons' logs via `ha addons logs <slug>`

## [1.2.42] - 2026-01-14

### Added
- `hassio_role: homeassistant` permission for reading core logs
- Fixes 403 error when using `ha core logs`

## [1.2.41] - 2026-01-14

### Added
- Installed Home Assistant CLI (`ha` command) in the container
- `ha core logs`, `ha core restart`, etc. now available

## [1.2.40] - 2026-01-14

### Fixed
- Updated log commands in CLAUDE.md (`ha` CLI not available in add-on containers)
- Now uses `/homeassistant/home-assistant.log` and Supervisor API

## [1.2.39] - 2026-01-14

### Added
- CLAUDE.md now includes Home Assistant logging instructions
  - Log levels explanation (debug, info, warning, error)
  - Commands to read and filter logs
  - How to enable debug logging for integrations

## [1.2.38] - 2026-01-14

### Added
- Pre-authorized read-only hass-mcp tools (no confirmation needed):
  - `get_version`, `get_entity`, `list_entities`, `search_entities_tool`
  - `domain_summary_tool`, `list_automations`, `get_history`, `get_error_log`
- Pre-authorized file read operations:
  - `Read`, `Glob`, `Grep` for `/homeassistant/**`, `/config/**`, `/share/**`, `/media/**`
- Write operations still require confirmation: `entity_action`, `call_service_tool`, `restart_ha`

## [1.2.37] - 2026-01-14

### Added
- Auto-generated `~/.claude/CLAUDE.md` with path mapping instructions
- Claude Code now knows `/config` → `/homeassistant` translation

## [1.2.36] - 2026-01-14

### Fixed
- Reverted `/config` symlink that caused 502 startup errors

## [1.2.35] - 2026-01-14

### Added
- Symlink `/config` → `/homeassistant` for HA path compatibility (reverted in 1.2.36)

## [1.2.34] - 2026-01-14

### Added
- Auto-update Claude Code option (`auto_update_claude`) - checks for updates on startup
- Keeps Claude Code current without requiring add-on version bumps

## [1.2.33] - 2026-01-14

### Added
- Brazilian Portuguese translation (pt-BR)
- Spanish translation (es)

## [1.2.32] - 2026-01-14

### Fixed
- Added .profile to source .bashrc (tmux login shells need this for aliases)

## [1.2.31] - 2026-01-14

### Fixed
- Version bump to force rebuild (1.2.30 may have been cached before alias fix)

## [1.2.30] - 2026-01-14

### Changed
- Reorganized documentation: DOCS.md renamed to README.md
- Simplified root README.md
- Added Quick Start and Requirements sections

### Fixed
- Added .bashrc with aliases (`c`, `cc`, `ha-config`, `ha-logs`) - they were documented but not working

### Removed
- Deleted unused run.sh (Dockerfile CMD has everything inline)

## [1.2.29] - 2026-01-14

### Fixed
- hass-mcp expects `HA_URL` not `HA_HOST`

## [1.2.28] - 2026-01-14

### Changed
- Export HA_TOKEN/HA_HOST as environment variables instead of baking into MCP config
- hass-mcp now reads token from inherited environment (cleaner approach)

## [1.2.27] - 2026-01-14

### Fixed
- hass-mcp expects `HA_TOKEN` and `HA_HOST` (not `HASS_TOKEN`/`HASS_HOST`)

## [1.2.26] - 2026-01-14

### Fixed
- MCP now configured using `claude mcp add-json` command (proper Claude Code API)
- Previous settings.json approach was not recognized by Claude Code

### Documentation
- Added detailed copy/paste instructions for tmux mode (Ctrl+Shift to select, Shift+Insert to paste)

## [1.2.25] - 2026-01-14

### Fixed
- MCP configuration was never created - hass-mcp integration now works
- Added MCP setup to Dockerfile CMD (run.sh was not being executed)
- `/mcp` command now shows Home Assistant MCP server when `enable_mcp: true`

## [1.2.24] - 2026-01-14

### Added
- Improved tmux mouse wheel scrolling support
- Disable alternate screen buffer for better scrollback (`smcup@:rmcup@`)
- Mouse wheel bindings for scrolling in tmux copy mode

### Note
- Mouse scrolling now enabled; use middle-click or Shift+Insert to paste

## [1.2.23] - 2026-01-14

### Added
- Configure tmux with 20,000 line scrollback buffer (`history-limit`)
- Use `Ctrl+b [` then arrow keys/Page Up/Down to scroll in tmux

## [1.2.22] - 2026-01-14

### Added
- Increased terminal scrollback buffer to 20,000 lines (xterm.js)

## [1.2.21] - 2026-01-14

### Reverted
- Removed tmux mouse mode (breaks paste functionality)

### Documentation
- Added section explaining scrolling and session persistence trade-offs

## [1.2.20] - 2026-01-14

### Fixed
- Persist /root/.claude.json file (stores theme/onboarding state)
- Enable tmux mouse support for scroll wheel (`set -g mouse on`)

## [1.2.19] - 2026-01-14

### Fixed
- Store Claude Code data in /homeassistant/.claudecode (truly persistent)
- Survives addon uninstall/reinstall/rebuild
- Symlink ~/.claude and ~/.config/claude-code to HA config directory

## [1.2.18] - 2026-01-14

### Changed
- Sidebar icon changed to mdi:brain

### Fixed
- Persist both ~/.claude and ~/.config/claude-code directories
- Ensures all Claude Code auth and config survives restarts

## [1.2.17] - 2026-01-14

### Fixed
- Persist Claude Code authentication across restarts
- Symlink /root/.claude to /data/claude for persistent storage
- Restored config reading for font size, theme, and session persistence

## [1.2.16] - 2026-01-14

### Fixed
- Restored config reading for font size, theme, and session persistence
- ttyd now applies terminal_font_size, terminal_theme, and session_persistence settings

## [1.2.15] - 2026-01-14

### Fixed
- Refined AppArmor profile with focused permissions for HA config access
- Added dac_read_search capability for directory listing
- Full access to /homeassistant, /share, /media, /config directories
- Read-only access to system files, SSL, backups

## [1.2.14] - 2026-01-14

### Fixed
- Add /etc/** read permissions to AppArmor profile
- Fixes "bash: /etc/profile: Permission denied" error

## [1.2.13] - 2026-01-14

### Fixed
- Add PTY permissions to AppArmor profile (sys_tty_config, /dev/ptmx, /dev/pts/*)
- Fixes "pty_spawn: Permission denied" error when spawning terminal

## [1.2.12] - 2026-01-14

### Fixed
- Use static ttyd binary from GitHub releases instead of Alpine package
- Fixes "failed to load evlib_uv" libwebsockets error

## [1.2.11] - 2026-01-14

### Changed
- Simplified startup: run ttyd directly in CMD without script file
- Minimal configuration for debugging startup issues

## [1.2.10] - 2026-01-14

### Fixed
- Create run.sh inline via heredoc to avoid file permission issues

## [1.2.9] - 2026-01-14

### Fixed
- Add .gitattributes to enforce LF line endings for shell scripts
- Force Docker cache bust for permission fixes

## [1.2.8] - 2026-01-14

### Changed
- Use Docker's tini init system (`init: true`) instead of s6-overlay
- Simplified entrypoint configuration

## [1.2.7] - 2026-01-14

### Fixed
- Use bash instead of bashio in s6-overlay run script
- Add chmod +x /init to fix permission issues

## [1.2.6] - 2026-01-14

### Changed
- Properly configure s6-overlay v3 service structure
- Add service files in /etc/s6-overlay/s6-rc.d/ttyd

## [1.2.5] - 2026-01-14

### Changed
- Attempted switch to pure Alpine base image (reverted due to HA format requirements)

## [1.2.4] - 2026-01-14

### Fixed
- Set `init: false` for s6-overlay v3 compatibility

## [1.2.3] - 2026-01-14

### Fixed
- Force bash entrypoint to bypass s6-overlay init issues

## [1.2.2] - 2026-01-14

### Fixed
- Remove s6-overlay dependency, use plain bash with jq
- Fixes "/init: Permission denied" startup error

## [1.2.1] - 2026-01-14

### Fixed
- Corrected hass-mcp package name (was homeassistant-mcp)
- Upgraded to Python 3.13 base image for hass-mcp compatibility

## [1.2.0] - 2026-01-14

### Changed
- **Security improvement**: Removed API key from add-on config - Claude Code now handles authentication itself
- Simplified Dockerfile - use Alpine's ttyd package instead of architecture-specific downloads
- Removed model selection from config (Claude Code manages this)

### Fixed
- Docker build failure due to BUILD_ARCH variable not being passed correctly

## [1.1.0] - 2026-01-14

### Added
- Model selection option (sonnet, opus, haiku)
- Terminal font size configuration (10-24px)
- Terminal theme selection (dark/light)
- Session persistence using tmux
- s6-overlay service definitions for better process management
- Shell aliases and shortcuts (c, cc, ha-config, ha-logs)
- Welcome banner with configuration info
- Health check for container monitoring

### Changed
- Upgraded to Python 3.12 Alpine base image
- Improved architecture-specific ttyd binary installation
- Enhanced run.sh with better configuration handling
- Better error messages and validation

### Fixed
- Proper ingress base path handling

## [1.0.0] - 2026-01-14

### Added
- Initial release
- Web terminal interface using ttyd
- Claude Code integration via npm package
- Home Assistant MCP server integration for entity/service access
- Read-write access to Home Assistant configuration
- Multi-architecture support (amd64, aarch64, armv7, armhf, i386)
- Ingress support for seamless sidebar integration
