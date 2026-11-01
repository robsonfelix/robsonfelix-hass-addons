# Changelog

All notable changes to this project will be documented in this file.

## [0.1.13] - 2026-11-01

### Changed
- Upgraded the base image to `mcr.microsoft.com/playwright:v1.64.1-noble` (from `v1.57.0-noble`). The add-on was seven minor Playwright releases behind, while the Claude Code add-on installs `@playwright/mcp` unpinned and therefore tracks the newest client — currently one built against `playwright 1.65.0-alpha`. Client and browser are released together and expect to match, so the gap was widening silently with every rebuild

### Fixed
- `README.md` quoted `v1.50.0-noble` as the base image, two upgrades out of date. The version number is gone from the README entirely: it points at the Dockerfile instead, which is the only place that cannot go stale
- Documented the version coupling between this add-on's browser and the `@playwright/mcp` client the Claude Code add-on installs, including what a mismatch looks like

## [0.1.12] - 2026-02-24

### Fixed
- The Dockerfile uses `mcr.microsoft.com/playwright` as its base image directly instead of the `BUILD_FROM` arg. The Home Assistant builder's image regex does not accept MCR references, so the arg silently fell back to the Alpine base and the resulting image had no Chromium. This entry was reconstructed after the fact — 0.1.12 shipped without a changelog entry, which the repository's new CI check now prevents

## [0.1.11] - 2026-02-23

### Added
- aarch64 (ARM64) architecture support for Raspberry Pi 4/5, ODROID, etc.
- `build.yaml` for multi-architecture builds via HA builder
- Dockerfile now uses `BUILD_FROM` arg pattern (consistent with other add-ons)

## [0.1.10] - 2026-01-15

### Fixed
- Use nginx `sub_filter` to rewrite WebSocket URLs in Chrome's responses
- Chrome returns `ws://localhost/...` which doesn't work across containers
- Now rewrites to `ws://{container-hostname}:{port}/...` for proper cross-container access

## [0.1.9] - 2026-01-15

### Fixed
- Replace `wait -n` with proper process monitoring loop
- Add sleep after nginx start and check both processes every 5 seconds
- Better error reporting (shows which process exited)

## [0.1.8] - 2026-01-15

### Fixed
- Run nginx in foreground mode (`daemon off`) to prevent immediate exit
- Fixes add-on starting then immediately stopping

## [0.1.7] - 2026-01-15

### Fixed
- Use nginx reverse proxy instead of socat
- nginx rewrites Host header to 'localhost' (Chrome v66+ security requirement)
- Fixes "Host header is specified and is not an IP address or localhost" error
- Full WebSocket support with proper upgrade headers

## [0.1.6] - 2026-01-15

### Fixed
- Use socat TCP forwarder to expose CDP port externally
- Chrome ignores all attempts to bind to 0.0.0.0, so we forward port 9222 to Chrome's localhost:9223
- Should definitively fix connection refused errors from other containers

## [0.1.5] - 2026-01-15

### Fixed
- Added `--remote-debugging-bind-to-all-interfaces` flag for newer Chrome versions
- Fixes Chrome ignoring `--remote-debugging-address=0.0.0.0` and binding only to localhost

## [0.1.4] - 2026-01-15

### Changed
- Upgraded to Playwright v1.57.0 (from v1.50.0)

## [0.1.3] - 2026-01-15

### Changed
- Added more Chromium flags to reduce noise from dbus/GCM errors
- Disabled notifications, permissions API, background mode, and other unused features
- Added info message explaining dbus errors are harmless in containerized environments

## [0.1.2] - 2026-01-15

### Fixed
- Reverted to `--headless` (without `=new`) for compatibility
- Added `--remote-allow-origins=*` to allow cross-origin CDP connections
- Removed `about:blank` URL that may have caused early exit
- Added more flags to reduce noise and disable unnecessary features

## [0.1.1] - 2026-01-15

### Fixed
- Hardcode Playwright base image in Dockerfile (HA's build_from regex doesn't support MCR format)
- Removed build.yaml, using direct FROM instruction
- Limited to amd64 architecture for now

## [0.1.0] - 2026-01-15

### Added
- Initial release
- Headless Chromium browser with CDP endpoint
- Based on official Microsoft Playwright Docker image
- Exposes Chrome DevTools Protocol on configurable port
- Designed for use with Claude Code's Playwright MCP
