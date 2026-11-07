# Claude Code Instructions

This file contains instructions for Claude Code when working on this repository.

## Before Every Commit

**IMPORTANT:** Update `claudecode/CHANGELOG.md` with the changes being committed before making any commit. Follow the existing format:

```markdown
## [VERSION] - YYYY-MM-DD

### Added/Changed/Fixed
- Description of change
```

## Running Tests

Run `make test` from the repo root: it installs the test dependencies
(`claudecode/tests/requirements.txt`) and runs unittest discovery from the right
directory. A single module: `make test P=test_login_url.py`. Dotted module names
(`python3 -m unittest tests.test_login_url`) do not work.

## Project Structure

- `Makefile` - `make test` / `make deps` for the test-suite
- `repository.yaml` - Add-on repository metadata
- `claudecode/` - Claude Code add-on
  - `config.yaml` - Add-on configuration (bump version here)
  - `Dockerfile` - Container build instructions
  - `build.yaml` - Multi-architecture build settings
  - `README.md` - User documentation (shown as the add-on's Documentation tab)
  - `tests/` - Test-suite (`make test`)
  - `CHANGELOG.md` - Version history (**update before commits**)
  - `apparmor.txt` - Security profile

## Version Bumping

Every add-on declares `image: ghcr.io/robsonfelix/<addon>-{arch}` in its
`config.yaml`, so the Supervisor **pulls** that image and never builds locally.
That makes the release order load-bearing: if `main` announces a version whose
image is not in the registry yet, every install and update of that add-on fails
outright, with no local-build fallback to save it.

So push the tag **before** the branch:

1. Update the version in `<addon>/config.yaml`
2. Add an entry to `<addon>/CHANGELOG.md`
3. Commit, but do not push the branch yet
4. `git push origin <addon>/v<version>` - the tag carries the commit, CI builds
   it and publishes `<addon>-{arch}:<version>` to ghcr.io
5. Wait for that workflow to go green, then `git push origin main`

Done in this order nobody ever sees a version whose image does not exist. Confirm
the image landed before step 5:

```bash
t=$(curl -s "https://ghcr.io/token?scope=repository:robsonfelix/<addon>-amd64:pull&service=ghcr.io" | jq -r .token)
curl -s -H "Authorization: Bearer $t" "https://ghcr.io/v2/robsonfelix/<addon>-amd64/tags/list" | jq .tags
```

A change that touches only `config.yaml` (and not the image contents) needs no
bump at all - the Supervisor reads `config.yaml` from the store, so it reaches
new installs on the next repository refresh.

## Home Assistant Add-on Notes

- Rebuild button only rebuilds from cached config
- To pick up config.yaml changes: uninstall/reinstall or bump version and update
- Base images use s6-overlay v3 - be careful with init configuration
- `init: true` uses Docker's tini, `init: false` uses s6-overlay's /init
