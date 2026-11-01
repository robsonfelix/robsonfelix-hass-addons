# Playwright Browser Add-on

Headless Chromium browser with Chrome DevTools Protocol (CDP) endpoint for browser automation.

## Overview

This add-on runs a headless Chromium browser that exposes a CDP endpoint, allowing other add-ons (like Claude Code) to connect and perform browser automation tasks.

Based on the official [Microsoft Playwright Docker image](https://playwright.dev/docs/docker).
The exact tag is pinned in [`Dockerfile`](./Dockerfile) — check there rather than
trusting a version number quoted here, which is how this line went stale for
seven releases.

### Version coupling with Claude Code

Playwright's client and browser are released together and expect to match. The
Claude Code add-on installs `@playwright/mcp` **unpinned**, so each rebuild picks
up the newest release, while the browser served here moves only when this
Dockerfile is bumped. The two therefore drift apart on their own.

CDP is stable enough that a modest gap usually works, but it is not a supported
combination. If browser automation starts failing in ways that look like protocol
errors, compare the Playwright version bundled with `@playwright/mcp` against the
tag in this add-on's Dockerfile, and bump this one.

## Installation

1. Add this repository to Home Assistant
2. Install the "Playwright Browser" add-on
3. Start the add-on (it does NOT auto-start by default)
4. The CDP endpoint will be available at `ws://local-playwright-browser:9222`

## Usage with Claude Code

1. Install and start this add-on
2. In Claude Code configuration, enable "Playwright MCP"
3. Restart Claude Code
4. Claude Code will automatically connect to this browser for web automation

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `cdp_port` | 9222 | Port for the CDP endpoint |

## Architecture

```
┌─────────────────────┐     CDP WebSocket              ┌─────────────────────┐
│   Claude Code       │ ─────────────────────────────> │  Playwright Browser │
│   (Alpine, ~100MB)  │  ws://local-playwright-browser │  (Ubuntu, ~2GB)     │
│                     │           :9222                │                     │
│  @playwright/mcp    │                                │  Headless Chromium  │
└─────────────────────┘                                └─────────────────────┘
```

## Why a separate add-on?

Playwright/Chromium requires Ubuntu/Debian (glibc) to work properly. Home Assistant's default add-on base is Alpine (musl), which is incompatible with Chromium's sandbox requirements.

This add-on uses the official Playwright Docker image (Ubuntu-based) while keeping Claude Code lightweight on Alpine (~100MB vs ~2GB).

## Supported Architectures

- amd64 (x86_64)

Note: ARM64 (aarch64) support may be added in a future release once tested.

## Network

| Port | Description |
|------|-------------|
| 9222/tcp | Chrome DevTools Protocol (CDP) endpoint |

## Troubleshooting

**Add-on won't start?**
- Check the logs in Supervisor → Playwright Browser → Log
- Ensure you have enough disk space (~2GB for the image)

**Claude Code can't connect?**
- Make sure this add-on is running before enabling Playwright MCP in Claude Code
- Restart Claude Code after enabling Playwright MCP
