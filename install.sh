#!/bin/bash
# CS3NEWS GIGAVPN Installer

set -e

REPO_URL="https://github.com/QUALITY-SUPREMACY/cs3news-gigavpn.git"
INSTALL_DIR="${HOME}/.local/share/cs3news-gigavpn"
VENV_DIR="${INSTALL_DIR}/venv"

echo "🚀 Installing CS3NEWS GIGAVPN..."

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
    echo "📥 Updating..."
    git pull
else
    echo "📥 Cloning..."
    git clone "${REPO_URL}" .
fi

# Create virtual environment
echo "🐍 Creating venv..."
python3 -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

# Install dependencies
echo "📦 Installing deps..."
pip install --upgrade pip -q
pip install -r requirements.txt -q

# Create launch script
mkdir -p "${HOME}/.local/bin"
cat > "${HOME}/.local/bin/cs3news-gigavpn" << EOF
#!/bin/bash
source "${VENV_DIR}/bin/activate"
cd "${INSTALL_DIR}"
exec python -m proxy.main "\$@"
EOF

chmod +x "${HOME}/.local/bin/cs3news-gigavpn"

# Add to PATH
if [[ ":$PATH:" != *":${HOME}/.local/bin:"* ]]; then
    echo 'export PATH="${HOME}/.local/bin:${PATH}"' >> "${HOME}/.bashrc"
    echo "⚠️  Restart shell or: source ~/.bashrc"
fi

# Create default config
if [ ! -f "${INSTALL_DIR}/.env" ]; then
    cat > "${INSTALL_DIR}/.env" << 'EOF'
# CS3NEWS GIGAVPN Config
PROXY_HOST=127.0.0.1
PROXY_PORT=1080
WS_POOL_SIZE=8
WS_POOL_MAX_AGE=120
LOG_LEVEL=INFO
EOF
fi

echo ""
echo "✅ Installed!"
echo ""
echo "🚀 Run: cs3news-gigavpn"
echo "⚙️  Config: ${INSTALL_DIR}/.env"
