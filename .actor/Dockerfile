FROM python:3.11-slim-bookworm


RUN groupadd -r appuser && useradd -r -g appuser -s /sbin/nologin appuser && \
    \
    apt-get update && apt-get install -y --no-install-recommends bash curl file git gpg jo jq procps xz-utils && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && apt-get install -y nodejs && apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    \
    pip install --no-cache-dir docling && \
    npm install -g apify-cli && \
    npm cache clean --force

WORKDIR /app

RUN mkdir -p /tmp/runtime-root && \
    chmod 0700 /tmp/runtime-root && \
    chown appuser:appuser /tmp/runtime-root

COPY --chown=appuser:appuser .actor/ .actor/
COPY --chown=appuser:appuser . .

USER appuser

ENTRYPOINT [".actor/actor.sh"]
