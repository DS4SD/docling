FROM ds4sd/docling-serve:latest

LABEL maintainer="Vaclav Vancura <@vancura>"
LABEL description="Apify Actor for document processing using Docling"
LABEL version="1.1.0"

# Install necessary dependencies for the Apify Actor
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gpg \
    jq \
    xz-utils \
    jo \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for Apify CLI
RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/* && \
    npm install -g npm@latest && \
    npm install -g apify-cli && \
    npm cache clean --force

# Create directories and set permissions
WORKDIR /app

# Copy actor files
COPY --chown=1000:1000 .actor/ .actor/

# Security best practice: run as non-root user (docling-serve already uses a non-root user)
USER 1000

ENTRYPOINT [".actor/actor.sh"]
