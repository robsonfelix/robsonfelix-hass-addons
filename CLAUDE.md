# Claude Code Instructions

This file contains instructions for Claude Code when working on this repository.

## Before Every Commit

**IMPORTANT:** Update `claudecode/CHANGELOG.md` with the changes being committed before making any commit. Follow the existing format:

```markdown
## [VERSION] - YYYY-MM-DD

### Added/Changed/Fixed
- Description of change
```

## Project Structure

- `repository.yaml` - Add-on repository metadata
- `claudecode/` - Claude Code add-on
  - `config.yaml` - Add-on configuration (bump version here)
  - `Dockerfile` - Container build instructions
  - `build.yaml` - Multi-architecture build settings
  - `README.md` - User documentation (shown as the add-on's Documentation tab)
  - `CHANGELOG.md` - Version history (**update before commits**)
  - `apparmor.txt` - Security profile

## Version Bumping

When making changes that require a new release:
1. Update version in `claudecode/config.yaml`
2. Add entry to `claudecode/CHANGELOG.md`
3. Commit and push

## Home Assistant Add-on Notes

- Rebuild button only rebuilds from cached config
- To pick up config.yaml changes: uninstall/reinstall or bump version and update
- Base images use s6-overlay v3 - be careful with init configuration
- `init: true` uses Docker's tini, `init: false` uses s6-overlay's /init
