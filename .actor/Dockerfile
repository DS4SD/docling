FROM python:3.11-slim

RUN apt-get update && apt-get install -y file procps curl gpg

RUN mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list

RUN apt-get update && apt-get install -y nodejs bash git jq jo xz-utils && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir docling

RUN npm install -g apify-cli && npm cache clean --force

WORKDIR /app

RUN mkdir -p /tmp/runtime-root && chmod 0700 /tmp/runtime-root

COPY .actor/ .actor/
COPY . .

ENTRYPOINT [".actor/actor.sh"]
