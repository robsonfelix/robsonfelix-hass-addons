# Changelog

All notable changes to this project will be documented in this file.

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
