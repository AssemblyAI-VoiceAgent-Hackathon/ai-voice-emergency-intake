FROM node:20-bookworm-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-venv build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY package.json package-lock.json ./
RUN npm ci

COPY requirements-dev.txt ./requirements-dev.txt
COPY src/voice/requirements.txt ./voice-requirements.txt
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements-dev.txt -r voice-requirements.txt
ENV PATH="/opt/venv/bin:$PATH"

COPY . .

RUN npm run build

# Backend and voice stay on the container's loopback interface; the
# dashboard is the only process Railway exposes publicly, and its
# next.config.mjs rewrites (/role3, /role1) proxy to these internally.
ENV ARIA_BIND_HOST=127.0.0.1 \
    ARIA_BIND_PORT=8000 \
    ARIA_VOICE_BIND_HOST=127.0.0.1 \
    ARIA_VOICE_BIND_PORT=8001

RUN chmod +x start-all.sh

CMD ["./start-all.sh"]
