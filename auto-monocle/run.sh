#!/usr/bin/with-contenv bashio
set -e

echo "========================================"
echo "  Auto-Monocle Add-on Starting"
echo "========================================"

MONOCLE_CONFIG="/etc/monocle/monocle.json"

# Read configuration
MONOCLE_TOKEN=$(bashio::config 'monocle_token')
AUTO_DISCOVER=$(bashio::config 'auto_discover')
REFRESH_INTERVAL=$(bashio::config 'refresh_interval')

if [ -z "$MONOCLE_TOKEN" ] || [ "$MONOCLE_TOKEN" = "null" ]; then
    bashio::log.error "Monocle token not configured!"
    bashio::log.error "Get your token from https://monoclecam.com and add it to the add-on configuration."
    exit 1
fi

# Run camera discovery (also writes token file)
bashio::log.info "Running camera discovery..."
python3 /opt/monocle/discover_cameras.py

if [ ! -f "/etc/monocle/monocle.token" ]; then
    bashio::log.error "Monocle token file not created!"
    exit 1
fi

if [ "$AUTO_DISCOVER" = "true" ] && [ ! -f "$MONOCLE_CONFIG" ]; then
    bashio::log.error "Monocle configuration not generated!"
    exit 1
fi

# Get initial config hash
CONFIG_HASH=$(md5sum "$MONOCLE_CONFIG" 2>/dev/null | cut -d' ' -f1 || echo "none")

# Start camera refresh in background (restarts gateway on changes)
if [ "$AUTO_DISCOVER" = "true" ]; then
    (
        while true; do
            sleep "$REFRESH_INTERVAL"
            bashio::log.info "Refreshing camera list..."
            python3 /opt/monocle/discover_cameras.py

            # Check if config changed
            NEW_HASH=$(md5sum "$MONOCLE_CONFIG" 2>/dev/null | cut -d' ' -f1 || echo "none")
            if [ "$NEW_HASH" != "$CONFIG_HASH" ]; then
                bashio::log.info "Camera configuration changed, restarting Monocle Gateway..."
                CONFIG_HASH="$NEW_HASH"
                pkill -f monocle-gateway || true
                sleep 2
                cd /opt/monocle
                ./monocle-gateway &
                bashio::log.info "Monocle Gateway restarted"
            else
                bashio::log.info "No camera changes detected"
            fi
        done
    ) &
fi

bashio::log.info "Starting Monocle Gateway..."
bashio::log.info "Make sure port 443 is forwarded to this add-on"

# Start Monocle Gateway (in foreground to keep container alive)
cd /opt/monocle
./monocle-gateway &
GATEWAY_PID=$!

# Wait for gateway process
wait $GATEWAY_PID
