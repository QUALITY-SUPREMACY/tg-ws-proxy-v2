#!/bin/bash
# Quick test for CS3NEWS GIGAVPN

set -e

echo "🧪 Testing CS3NEWS GIGAVPN..."

# Test 1: Check installation
echo -n "✓ Installation... "
if command -v cs3news-gigavpn > /dev/null 2>&1; then
    echo "OK"
else
    echo "FAIL (not in PATH)"
    exit 1
fi

# Test 2: Start proxy in background
echo -n "✓ Starting proxy... "
cs3news-gigavpn > /tmp/gigavpn-test.log 2>&1 &
PROXY_PID=$!
sleep 2

# Test 3: Check port is listening
echo -n "✓ Port 1080... "
if nc -z 127.0.0.1 1080 2>/dev/null || lsof -i :1080 > /dev/null 2>&1; then
    echo "OK"
else
    echo "FAIL"
    kill $PROXY_PID 2>/dev/null || true
    exit 1
fi

# Test 4: Test SOCKS5 handshake
echo -n "✓ SOCKS5 handshake... "
python3 << 'EOF' 2>/dev/null
import socket
import struct

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.settimeout(5)
s.connect(('127.0.0.1', 1080))

# Send greeting
s.send(bytes([0x05, 0x01, 0x00]))

# Read response
resp = s.recv(2)
if resp[0] == 0x05 and resp[1] == 0x00:
    print("OK")
else:
    print("FAIL")
    exit(1)

s.close()
EOF

# Test 5: Check Telegram IP detection (simulate)
echo -n "✓ Telegram IP detection... "
cd ~/.local/share/cs3news-gigavpn
python3 -c "
from proxy.telegram_const import is_telegram_ip
if is_telegram_ip('149.154.167.220'):
    print('OK')
else:
    print('FAIL')
    exit(1)
" 2>/dev/null

# Stop proxy
echo -n "✓ Stopping proxy... "
kill $PROXY_PID 2>/dev/null || true
wait $PROXY_PID 2>/dev/null || true
echo "OK"

echo ""
echo "✅ All tests passed!"
echo ""
echo "🚀 Ready to use:"
echo "   cs3news-gigavpn"
echo ""
echo "🔧 Then configure Telegram Desktop:"
echo "   Settings → Advanced → Connection type → SOCKS5 127.0.0.1:1080"