#!/bin/bash
set -e

echo "========================================"
echo "  Playwright Browser Add-on Starting"
echo "========================================"

# Read configuration
CDP_PORT=$(jq -r '.cdp_port // 9222' /data/options.json)

echo "[INFO] CDP port: ${CDP_PORT}"

# Find Chromium executable (Playwright installs it in /ms-playwright/)
CHROMIUM_PATH=$(find /ms-playwright -name "chrome" -type f 2>/dev/null | head -1)

if [ -z "$CHROMIUM_PATH" ]; then
    # Fallback to system chromium
    CHROMIUM_PATH=$(which chromium-browser 2>/dev/null || which chromium 2>/dev/null || which google-chrome 2>/dev/null || echo "")
fi

if [ -z "$CHROMIUM_PATH" ]; then
    echo "[ERROR] Chromium not found!"
    exit 1
fi

echo "[INFO] Using Chromium: ${CHROMIUM_PATH}"

# Create user data directory
USER_DATA_DIR="/tmp/chromium-data"
mkdir -p "$USER_DATA_DIR"

echo "[INFO] Starting Chromium with remote debugging on port ${CDP_PORT}..."
echo "[INFO] CDP endpoint: ws://local-playwright-browser:${CDP_PORT}"
echo "[INFO] (dbus errors below are harmless - no system bus in container)"

# Start Chromium in headless mode with remote debugging
# Note: dbus errors are expected and harmless in containerized environments
exec "$CHROMIUM_PATH" \
    --headless \
    --disable-gpu \
    --no-sandbox \
    --disable-setuid-sandbox \
    --disable-dev-shm-usage \
    --disable-software-rasterizer \
    --remote-debugging-port="${CDP_PORT}" \
    --remote-debugging-address=0.0.0.0 \
    --user-data-dir="$USER_DATA_DIR" \
    --disable-background-networking \
    --disable-default-apps \
    --disable-extensions \
    --disable-sync \
    --disable-translate \
    --disable-features=TranslateUI,BlinkGenPropertyTrees \
    --metrics-recording-only \
    --mute-audio \
    --no-first-run \
    --safebrowsing-disable-auto-update \
    --disable-breakpad \
    --disable-component-update \
    --disable-domain-reliability \
    --disable-features=AudioServiceOutOfProcess \
    --disable-print-preview \
    --disable-speech-api \
    --no-pings \
    --remote-allow-origins=*
