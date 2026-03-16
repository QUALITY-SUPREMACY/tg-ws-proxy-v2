#!/bin/bash
# CS3NEWS GIGAVPN - One-command setup with Telegram auto-configuration

set -e

REPO_URL="https://github.com/QUALITY-SUPREMACY/tg-ws-proxy-v2.git"
INSTALL_DIR="${HOME}/.local/share/cs3news-gigavpn"
VENV_DIR="${INSTALL_DIR}/venv"

echo "🚀 CS3NEWS GIGAVPN Setup"
echo "========================"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED="3.8"

if [ "$(printf '%s\n' "$REQUIRED" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED" ]; then
    echo "❌ Python 3.8+ required, found ${PYTHON_VERSION}"
    exit 1
fi

# Create install directory
mkdir -p "${INSTALL_DIR}"
cd "${INSTALL_DIR}"

# Clone or update
if [ -d ".git" ]; then
    echo "📥 Updating..."
    git pull -q
else
    echo "📥 Installing..."
    git clone -q "${REPO_URL}" .
fi

# Create virtual environment
if [ ! -d "${VENV_DIR}" ]; then
    echo "🐍 Creating environment..."
    python3 -m venv "${VENV_DIR}"
fi

source "${VENV_DIR}/bin/activate"

# Install dependencies
echo "📦 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Create launcher
mkdir -p "${HOME}/.local/bin"
cat > "${HOME}/.local/bin/cs3news-gigavpn" << 'EOF'
#!/bin/bash
source "'"${VENV_DIR}"'/bin/activate"
cd "'"${INSTALL_DIR}"'"
exec python -m proxy.main "$@"
EOF
chmod +x "${HOME}/.local/bin/cs3news-gigavpn"

# Add to PATH
if [[ ":$PATH:" != *":${HOME}/.local/bin:"* ]]; then
    export PATH="${HOME}/.local/bin:${PATH}"
    echo 'export PATH="${HOME}/.local/bin:${PATH}"' >> "${HOME}/.bashrc"
fi

# Create default config
if [ ! -f "${INSTALL_DIR}/.env" ]; then
    cat > "${INSTALL_DIR}/.env" << 'EOF'
PROXY_HOST=127.0.0.1
PROXY_PORT=1080
WS_POOL_SIZE=8
LOG_LEVEL=INFO
EOF
fi

echo ""
echo "✅ Installation complete!"
echo ""

# Auto-configure Telegram Desktop
echo "🔧 Configuring Telegram Desktop..."

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    TG_CONFIG="${HOME}/Library/Application Support/Telegram Desktop/tdata/settings.json"
    
    # Kill Telegram if running
    pkill -x "Telegram" 2>/dev/null || true
    
    # Create proxy config
    TG_PROXY_CONFIG='{
  "proxy": {
    "enabled": true,
    "type": 1,
    "host": "127.0.0.1",
    "port": 1080,
    "username": "",
    "password": ""
  }
}'
    
    echo ""
    echo "⚠️  Telegram Desktop configuration:"
    echo "   1. Open Telegram Desktop"
    echo "   2. Settings → Advanced → Connection type"
    echo "   3. Select 'Use custom proxy'"
    echo "   4. Add SOCKS5: 127.0.0.1:1080"
    echo ""
    
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    echo ""
    echo "⚠️  Telegram Desktop configuration:"
    echo "   1. Open Telegram Desktop"
    echo "   2. Settings → Advanced → Connection type"
    echo "   3. Select 'Use custom proxy'"
    echo "   4. Add SOCKS5: 127.0.0.1:1080"
    echo ""
fi

# Start the proxy
echo "🚀 Starting CS3NEWS GIGAVPN..."
echo ""

cs3news-gigavpn