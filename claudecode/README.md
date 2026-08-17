# Claude Code for Home Assistant

Run [Claude Code](https://docs.anthropic.com/en/docs/claude-code), Anthropic's AI-powered coding assistant, directly in your Home Assistant sidebar with full access to your configuration.

## Quick Start

```bash
claude "List all my automations"
claude "Turn off all lights in the living room"
claude "Create an automation to turn on lights at sunset"
claude "Why isn't my motion sensor automation working?"
```

## Requirements

- Home Assistant OS or Supervised installation
- [Anthropic account](https://console.anthropic.com/) (authentication handled in terminal)

## Features

- **Web Terminal**: Access Claude Code through a browser-based terminal
- **Config Access**: Read and write Home Assistant configuration files
- **hass-mcp Integration**: Direct control of HA entities and services
- **Session Persistence**: Optional tmux integration to preserve sessions across page refreshes
- **Customizable Theme**: Choose between dark and light terminal themes
- **Multi-Architecture**: Supports amd64, aarch64, armv7, armhf, and i386
- **Secure Authentication**: Claude Code handles its own authentication securely

## Setup

### 1. Install the Add-on

1. Add the repository to Home Assistant
2. Install the "Claude Code" add-on
3. Start the add-on
4. Open the Web UI from the sidebar

### 2. Authenticate with Claude Code

On first launch, Claude Code will prompt you to authenticate:

1. Open the terminal from the HA sidebar
2. Type `claude` to start
3. Follow the authentication prompts
4. Your credentials are stored securely by Claude Code

**Note**: The add-on does NOT require you to enter API keys in the configuration. Claude Code handles authentication itself, storing credentials securely in its own configuration directory. This is more secure than storing keys in Home Assistant's add-on config.

## Using Claude Code

### Basic Usage

Once authenticated, Claude Code is ready to help with:

- Editing Home Assistant YAML configurations
- Creating automations and scripts
- Debugging configuration issues
- Writing custom integrations

### Home Assistant Integration

With hass-mcp enabled, Claude can:

- Query entity states: "What's the temperature in the living room?"
- Control devices: "Turn off all lights in the bedroom"
- List services: "What services are available for climate control?"
- Debug automations: "Why didn't my morning routine trigger?"

### Example Commands

```bash
# Start interactive session
claude

# One-off commands
claude "Add a new automation that turns on the porch light at sunset"
claude "Check my configuration.yaml for errors"
claude "List all unavailable entities"

# Continue previous conversation
claude --continue
```

### Keyboard Shortcuts

| Shortcut | Command |
|----------|---------|
| `c` | `claude` |
| `cc` | `claude --continue` |
| `ha-config` | Navigate to config directory |
| `ha-logs` | View Home Assistant logs |

## Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `enable_mcp` | Enable HA integration | true |
| `enable_playwright_mcp` | Enable browser automation via the Playwright Browser add-on | false |
| `playwright_cdp_host` | Override the Playwright Browser hostname (auto-detected when empty) | "" |
| `terminal_font_size` | Font size (10-24) | 14 |
| `terminal_theme` | dark or light | dark |
| `working_directory` | Start directory | /homeassistant |
| `session_persistence` | Use tmux for persistent sessions | true |
| `auto_update_claude` | Auto-update Claude Code on startup (rolls back automatically if the new release cannot run) | true |
| `enable_remote_control` | View and steer the session from claude.ai/code or the Claude mobile app. See the security note below | false |
| `remote_control_session_prefix` | Prefix for auto-generated Remote Control session names | HomeAssistant |

### Remote Control

With `enable_remote_control`, sessions can be driven from `claude.ai/code` or the Claude mobile app (requires a Pro, Max, Team, or Enterprise subscription; API keys are not supported).

**Security note:** this add-on runs as root with full access to your Home Assistant host. Anyone who can sign in to the linked Claude account can control it. Leave this off unless you need it.

## File Locations

| Path | Description | Access |
|------|-------------|--------|
| `/homeassistant` | HA configuration directory | read-write |
| `/share` | Shared folder | read-write |
| `/media` | Media folder | read-write |
| `/ssl` | SSL certificates | read-only |
| `/backup` | Backups | read-only |

## Session Persistence

When `session_persistence` is enabled, the add-on uses tmux to maintain your terminal session. This means:

- Your session survives browser refreshes
- You can disconnect and reconnect without losing context
- Claude Code conversations are preserved

### tmux Commands

If you're new to tmux:

| Key | Action |
|-----|--------|
| `Ctrl+b d` | Detach from session (keeps it running) |
| `Ctrl+b [` | Enter scroll/copy mode (use arrow keys) |
| Mouse wheel | Scroll up/down (auto-enters copy mode) |
| `q` | Exit scroll/copy mode |

### Customizing tmux

Anything you put in `/homeassistant/.claudecode/tmux.conf` is loaded last and overrides the defaults. That file lives in your config directory, so it survives restarts, rebuilds and reinstalls:

```bash
echo 'set -g mouse off' > /homeassistant/.claudecode/tmux.conf
```

Turning the mouse off restores native browser selection and copy/paste while keeping persistent sessions. Alternatively set `session_persistence: false` to drop tmux entirely.

### Copy and Paste in tmux

Since tmux captures mouse events, copy/paste works differently:

| Action | How to do it |
|--------|--------------|
| **Copy (tmux copy-mode)** | Scroll up (enters copy-mode), select, then copy — lands directly on your clipboard¹ |
| **Copy** | Hold `Ctrl+Shift` while selecting text with mouse |
| **Paste** | `Shift+Insert` or middle-click |
| **Alternative paste** | `Ctrl+Shift+V` (browser dependent) |

¹ OSC 52 needs **HTTPS or localhost** — on plain HTTP, use the modifier-key gesture instead. Bonus: copy-mode copies wrapped lines as one logical line, so long URLs come out intact.

**Note**: Regular right-click paste and simple mouse selection won't work because tmux intercepts these events for scrolling.

#### Authenticating Claude Code (first launch)

**Click the URL** — this works everywhere, including plain HTTP. It's a real hyperlink (OSC 8): even though it wraps, any row opens the complete URL in a new tab after a confirmation prompt.

Over **HTTPS** (or localhost), the CLI's **press `c` to copy** hint also works via OSC 52. On plain HTTP browsers block clipboard writes — use the click.

Don't drag-select the URL: its rows are separate lines and copy with line breaks. If you need it as text, **zoom out** (`Ctrl + -` / `Cmd + -`) until it fits on one line.

Then authenticate in the browser, copy the auth code, and paste it back with `Shift+Insert` or `Ctrl+Shift+V`.

### Scrolling and Session Persistence Trade-offs

**With tmux (`session_persistence: true`):**
- ✅ Session survives browser refresh/disconnect
- ✅ Can detach and reattach to running sessions
- ✅ Long-running Claude tasks continue in background
- ✅ Mouse wheel scrolling works (enters copy mode automatically)
- ✅ 20,000 line scrollback buffer
- ✅ Copy-mode copies and `claude`'s "press `c` to copy" go straight to your clipboard (HTTPS/localhost only)
- ✅ OSC 8 hyperlinks (e.g. the `/login` URL) open complete with one click
- ⚠️ Use middle-click or Shift+Insert to paste (right-click paste may not work)

**Without tmux (`session_persistence: false`):**
- ✅ Native browser scrolling
- ✅ Simpler terminal behavior
- ✅ Standard copy/paste behavior
- ❌ Session lost on browser refresh
- ❌ Session lost if add-on restarts

**Recommendation:**
- Use `session_persistence: true` (default) if you run long tasks or need to survive disconnects
- Use `session_persistence: false` if you need standard copy/paste behavior

## Security

### Authentication
- **No API keys in add-on config**: Claude Code handles authentication itself
- Credentials are stored securely in Claude Code's own directory (`~/.claude/`)
- This is more secure than storing keys in Home Assistant's configuration

### Container Security
- The Supervisor token is passed in via the environment and is not written to disk. Versions before 1.2.65 persisted it into `settings.json` inside your config directory, which is included in Home Assistant backups; 1.2.65 scrubs it on startup
- Claude Code's credentials live in `/homeassistant/.claudecode/`, part of your config directory and therefore included in backups. Treat HA backups as secrets
- File access is limited to mapped directories
- The add-on runs as root with `full_access`, Docker socket access, and the Supervisor API. Anything that can drive Claude Code here can control your Home Assistant host

## Troubleshooting

### Authentication issues

Claude Code manages its own authentication. If you have issues:
1. Type `claude` to start the authentication flow
2. Follow the prompts to log in or enter your API key
3. Credentials are saved automatically for future sessions

**Can't copy the URL or paste the auth code?** The terminal uses tmux, which changes how copy/paste works. See [Copy and Paste in tmux](#copy-and-paste-in-tmux) for instructions.

### hass-mcp not working

1. Verify `enable_mcp` is true in configuration
2. Check add-on logs for connection errors
3. Restart the add-on after configuration changes

### Add-on won't start, or the log stops after "Checking for Claude Code updates"

Your CPU probably doesn't expose **AVX**. Since 2.1.113, Claude Code is a Bun-compiled native binary whose JavaScript engine requires it, and every `claude` command — even `claude --version` — hangs without it. That blocks startup before the terminal server binds its port, so Home Assistant reports the add-on as unhealthy.

This is common on virtual machines using a generic CPU model. Check from any terminal on the host:

```bash
grep -o -m1 avx2 /proc/cpuinfo   # no output means AVX2 is missing
```

Fix it at the hypervisor, not in the add-on:

- **Proxmox**: VM → Hardware → Processor → Type: `host` (or `x86-64-v3`)
- **libvirt / virt-manager**: CPU model → *Copy host CPU configuration*
- **ESXi / UnRAID**: enable host CPU passthrough

Then fully **stop and start** the VM — a reboot alone doesn't re-negotiate the CPU model.

Until you do, the add-on still works: the build automatically falls back to Claude Code 2.1.112, the last release that runs without AVX, and startup prints a warning explaining this.

### Terminal not loading

1. Check that the add-on is running (green indicator)
2. Try refreshing the page
3. Check browser console for errors
4. Review add-on logs for ttyd errors

### Session not persisting

1. Ensure `session_persistence` is set to true
2. The session is named "claude" - it will auto-attach on reconnect

### Configuration changes not applying

After changing configuration:
1. Save the configuration
2. Restart the add-on completely

## Support

- [GitHub Issues](https://github.com/robsonfelix/robsonfelix-hass-addons/issues)
- [Home Assistant Community](https://community.home-assistant.io/)
