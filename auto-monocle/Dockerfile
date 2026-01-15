ARG BUILD_FROM
FROM ${BUILD_FROM}

# Labels
LABEL maintainer="Robson Felix"
LABEL org.opencontainers.image.title="Auto-Monocle for Home Assistant"
LABEL org.opencontainers.image.description="Auto-discover HA cameras and expose to Alexa via Monocle Gateway"
LABEL org.opencontainers.image.source="https://github.com/robsonfelix/robsonfelix-hass-addons"
LABEL org.opencontainers.image.licenses="MIT"

# Install dependencies
RUN apk add --no-cache \
    bash \
    curl \
    jq \
    python3 \
    py3-pip \
    py3-requests \
    openjdk11-jre-headless \
    ca-certificates \
    && update-ca-certificates

# Download Monocle Gateway v0.0.6
ARG BUILD_ARCH
RUN mkdir -p /opt/monocle /etc/monocle && \
    case "${BUILD_ARCH}" in \
        amd64) MONOCLE_ARCH="alpine-x64" ;; \
        aarch64) MONOCLE_ARCH="alpine-arm64" ;; \
        *) MONOCLE_ARCH="alpine-x64" ;; \
    esac && \
    curl -fsSL "https://files.monoclecam.com/monocle-gateway/linux/monocle-gateway-${MONOCLE_ARCH}-v0.0.6.tar.gz" -o /tmp/monocle.tar.gz && \
    tar -xzf /tmp/monocle.tar.gz -C /opt/monocle --strip-components=1 && \
    rm /tmp/monocle.tar.gz && \
    chmod +x /opt/monocle/monocle-gateway

# Copy scripts
COPY discover_cameras.py /opt/monocle/
COPY run.sh /opt/monocle/
RUN chmod +x /opt/monocle/run.sh

WORKDIR /opt/monocle

CMD ["/opt/monocle/run.sh"]
