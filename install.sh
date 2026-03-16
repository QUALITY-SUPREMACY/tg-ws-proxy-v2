#!/bin/bash
# One-command installer for tg-ws-proxy-v2

set -e

REPO_URL="https://github.com/Flowseal/tg-ws-proxy.git"
INSTALL_DIR="${HOME}/.local/share/tg-ws-proxy-v2"
VENV_DIR="${INSTALL_DIR}/venv"

echo "🚀 Installing tg-ws-proxy-v2..."

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

# Clone repository
if [ -d ".git" ]; then
    echo "📥 Updating repository..."
    git pull
else
    echo "📥 Cloning repository..."
    git clone "${REPO_URL}" .
fi

# Create virtual environment
echo "🐍 Creating virtual environment..."
python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create systemd service (Linux)
if command -v systemctl > /dev/null 2>&1; then
    echo "🔧 Creating systemd service..."
    
    cat > /tmp/tg-ws-proxy.service << EOF
[Unit]
Description=TG WS Proxy V2
After=network.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${INSTALL_DIR}
Environment=PATH=${VENV_DIR}/bin
ExecStart=${VENV_DIR}/bin/python -m proxy.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    echo "💡 To enable systemd service:"
    echo "   sudo mv /tmp/tg-ws-proxy.service /etc/systemd/system/"
    echo "   sudo systemctl daemon-reload"
    echo "   sudo systemctl enable --now tg-ws-proxy"
fi

# Create launch script
cat > "${HOME}/.local/bin/tg-ws-proxy" << EOF
#!/bin/bash
source "${VENV_DIR}/bin/activate"
cd "${INSTALL_DIR}"
exec python -m proxy.main "\$@"
EOF

chmod +x "${HOME}/.local/bin/tg-ws-proxy"

# Add to PATH if needed
if [[ ":$PATH:" != *":${HOME}/.local/bin:"* ]]; then
    echo 'export PATH="${HOME}/.local/bin:${PATH}"' >> "${HOME}/.bashrc"
    echo "⚠️  Please restart your shell or run: source ~/.bashrc"
fi

# Create default config
if [ ! -f "${INSTALL_DIR}/.env" ]; then
    cat > "${INSTALL_DIR}/.env" << 'EOF'
# TG WS Proxy V2 Configuration
PROXY_HOST=127.0.0.1
PROXY_PORT=1080
WS_POOL_SIZE=8
WS_POOL_MAX_AGE=120
LOG_LEVEL=INFO
EOF
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "🚀 Quick start:"
echo "   tg-ws-proxy"
echo ""
echo "⚙️  Edit config: ${INSTALL_DIR}/.env"
echo "📖 Documentation: ${INSTALL_DIR}/README.md"
echo ""
echo "🔧 Configure Telegram Desktop:"
echo "   Settings → Advanced → Connection type → Use custom proxy"
echo "   Add SOCKS5: 127.0.0.1:1080"
