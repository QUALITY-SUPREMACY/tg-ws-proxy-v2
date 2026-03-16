#!/bin/bash
# Docker one-liner installer

set -e

echo "🐳 Running tg-ws-proxy-v2 in Docker..."

# Check Docker
if ! command -v docker > /dev/null 2>&1; then
    echo "❌ Docker not found. Install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

# Run container
docker run -d \
    --name tg-ws-proxy-v2 \
    --restart unless-stopped \
    -p 1080:1080 \
    -e PROXY_HOST=0.0.0.0 \
    -e PROXY_PORT=1080 \
    -e WS_POOL_SIZE=8 \
    -e LOG_LEVEL=INFO \
    ghcr.io/flowseal/tg-ws-proxy-v2:latest

echo "✅ Proxy running on 127.0.0.1:1080"
echo ""
echo "🔧 View logs: docker logs -f tg-ws-proxy-v2"
echo "🛑 Stop: docker stop tg-ws-proxy-v2"
echo "🗑️  Remove: docker rm -f tg-ws-proxy-v2"
