# Build directly on the official Playwright image (Ubuntu Noble).
# It ships Chromium in /ms-playwright/ (required by run.sh) and has apt-get.
# NOTE: hardcoded instead of using BUILD_FROM/build.yaml because the HA
# Supervisor's build_from regex rejects single-segment image paths like
# "mcr.microsoft.com/playwright", silently falling back to the Alpine base.
FROM mcr.microsoft.com/playwright:v1.65.0-noble

# Labels
LABEL maintainer="Robson Felix"
LABEL io.hass.version="0.1.0"
LABEL io.hass.type="addon"
LABEL io.hass.arch="amd64,aarch64"
LABEL org.opencontainers.image.title="Playwright Browser for Home Assistant"
LABEL org.opencontainers.image.description="Headless Chromium with CDP endpoint for browser automation"
LABEL org.opencontainers.image.source="https://github.com/robsonfelix/robsonfelix-hass-addons"
LABEL org.opencontainers.image.licenses="MIT"

# jq is already available in the Playwright image (Ubuntu-based)
# Just ensure it's installed
RUN apt-get update && \
    apt-get install -y --no-install-recommends jq curl nginx && \
    rm -rf /var/lib/apt/lists/*

# Create data directory
RUN mkdir -p /data

# Copy run script
COPY run.sh /run.sh
RUN chmod +x /run.sh

# Expose CDP port
EXPOSE 9222

# Health check - verify CDP endpoint responds
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -sf http://localhost:9222/json/version || exit 1

CMD ["/run.sh"]
