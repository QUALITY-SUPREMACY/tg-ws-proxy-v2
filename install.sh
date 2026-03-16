#!/bin/bash
# CS3NEWS GIGAVPN - Fully automatic setup

set -e

REPO_URL="https://github.com/QUALITY-SUPREMACY/tg-ws-proxy-v2.git"
INSTALL_DIR="${HOME}/.local/share/cs3news-gigavpn"
VENV_DIR="${INSTALL_DIR}/venv"

echo "🚀 CS3NEWS GIGAVPN Auto-Setup"
echo "=============================="

# Check Python
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED="3.8"
if [ "$(printf '%s\n' "$REQUIRED" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED" ]; then
    echo "❌ Python 3.8+ required"
    exit 1
fi

# Install
mkdir -p "${INSTALL_DIR}"
cd "${INSTALL_DIR}"

if [ -d ".git" ]; then
    echo "📥 Updating..."
    git pull -q
else
    echo "📥 Installing..."
    git clone -q "${REPO_URL}" .
fi

# Setup venv
if [ ! -d "${VENV_DIR}" ]; then
    python3 -m venv "${VENV_DIR}"
fi
source "${VENV_DIR}/bin/activate"
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Create launcher
mkdir -p "${HOME}/.local/bin"
cat > "${HOME}/.local/bin/cs3news-gigavpn" << EOF
#!/bin/bash
source "${VENV_DIR}/bin/activate"
cd "${INSTALL_DIR}"
exec python -m proxy.main "\$@"
EOF
chmod +x "${HOME}/.local/bin/cs3news-gigavpn"

# Add to PATH
export PATH="${HOME}/.local/bin:${PATH}"
if ! grep -q "\.local/bin" "${HOME}/.bashrc" 2>/dev/null; then
    echo 'export PATH="${HOME}/.local/bin:${PATH}"' >> "${HOME}/.bashrc"
fi

# Create config
[ ! -f ".env" ] && echo -e "PROXY_HOST=127.0.0.1\nPROXY_PORT=1080\nWS_POOL_SIZE=8\nLOG_LEVEL=INFO" > ".env"

echo "✅ Installed!"

# Auto-configure Telegram
echo "🔧 Auto-configuring Telegram Desktop..."

# Kill Telegram
pkill -x "Telegram" 2>/dev/null || pkill -x "Telegram Desktop" 2>/dev/null || true
sleep 1

# macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    TG_DATA="${HOME}/Library/Application Support/Telegram Desktop/tdata"
    
    if [ -d "$TG_DATA" ]; then
        # Backup settings
        [ -f "$TG_DATA/settings.json" ] && cp "$TG_DATA/settings.json" "$TG_DATA/settings.json.backup"
        
        # Create proxy settings
        python3 << PYEOF
import json
import os

settings_path = os.path.expanduser("~/Library/Application Support/Telegram Desktop/tdata/settings.json")

settings = {}
if os.path.exists(settings_path):
    try:
        with open(settings_path, 'r') as f:
            settings = json.load(f)
    except:
        pass

settings['proxy'] = {
    'enabled': True,
    'type': 1,
    'host': '127.0.0.1',
    'port': 1080,
    'username': '',
    'password': ''
}

os.makedirs(os.path.dirname(settings_path), exist_ok=True)
with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=2)

print("✅ Telegram Desktop configured")
PYEOF
    else
        echo "⚠️  Telegram Desktop not found. Install it first."
    fi

# Linux
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    TG_CONFIGS=(
        "${HOME}/.local/share/TelegramDesktop/tdata/settings.json"
        "${HOME}/.var/app/org.telegram.desktop/data/Telegram Desktop/tdata/settings.json"
    )
    
    for TG_DATA in "${TG_CONFIGS[@]}"; do
        if [ -d "$(dirname "$TG_DATA")" ]; then
            [ -f "$TG_DATA" ] && cp "$TG_DATA" "$TG_DATA.backup"
            
            python3 << PYEOF
import json
import os

settings_path = "$TG_DATA"
settings = {}
if os.path.exists(settings_path):
    try:
        with open(settings_path, 'r') as f:
            settings = json.load(f)
    except:
        pass

settings['proxy'] = {
    'enabled': True,
    'type': 1,
    'host': '127.0.0.1',
    'port': 1080,
    'username': '',
    'password': ''
}

os.makedirs(os.path.dirname(settings_path), exist_ok=True)
with open(settings_path, 'w') as f:
    json.dump(settings, f, indent=2)

print("✅ Telegram Desktop configured")
PYEOF
            break
        fi
    done
fi

# Start proxy
echo ""
echo "🚀 Starting CS3NEWS GIGAVPN..."
echo "=============================="
echo ""
echo "✅ Proxy: 127.0.0.1:1080"
echo "✅ Telegram: Auto-configured"
echo ""
echo "📝 To stop: Ctrl+C"
echo ""

cs3news-gigavpn