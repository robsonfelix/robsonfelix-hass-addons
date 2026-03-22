# Changelog

All notable changes to this project will be documented in this file.

## [0.1.12] - 2026-03-22

### Fixed
- Hardcode Playwright base image in Dockerfile to bypass HA Supervisor regex validation
- HA Supervisor requires registry/org/image format but MCR uses registry/image (mcr.microsoft.com/playwright)
- Use dummy base images in build.yaml to pass validation, actual image set directly in Dockerfile

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
