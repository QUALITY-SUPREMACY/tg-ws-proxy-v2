# TG WS Proxy V2

[![Docker](https://github.com/Flowseal/tg-ws-proxy/actions/workflows/docker.yml/badge.svg)](https://github.com/Flowseal/tg-ws-proxy/actions/workflows/docker.yml)

Исправленная версия tg-ws-proxy для ускорения Telegram Desktop через WebSocket.

## ⚡ Быстрый старт

### Вариант 1: Docker (рекомендуется)

```bash
docker run -d --name tg-proxy -p 1080:1080 ghcr.io/flowseal/tg-ws-proxy-v2:latest
```

### Вариант 2: One-liner установка

```bash
curl -fsSL https://raw.githubusercontent.com/Flowseal/tg-ws-proxy/main/install.sh | bash
```

### Вариант 3: Ручная установка

```bash
git clone https://github.com/Flowseal/tg-ws-proxy.git
cd tg-ws-proxy
pip install -r requirements.txt
python -m proxy.main
```

## 🔧 Настройка Telegram Desktop

1. Откройте **Settings → Advanced → Connection type**
2. Выберите **"Use custom proxy"**
3. Добавьте SOCKS5: `127.0.0.1:1080`

## ✨ Что исправлено

| Проблема (v1) | Исправление (v2) |
|---------------|------------------|
| SSL verification отключён | ✅ Certificate pinning |
| Глобальный mutable state | ✅ Thread-safe классы |
| Sequential pool refill | ✅ Parallel asyncio.gather |
| Нет graceful shutdown | ✅ Корректное завершение |
| Нет rate limiting | ✅ DoS защита |
| SOCKS5 без auth | ✅ Опциональная auth |
| Монолитный код | ✅ 8 модулей |

## 📁 Структура

```
proxy/
├── main.py           # Entry point
├── config.py         # Pydantic settings
├── socks5.py         # SOCKS5 protocol
├── rate_limiter.py   # Rate limiting
├── pool.py           # WebSocket pool
├── websocket.py      # SSL pinning
├── bridge.py         # Traffic bridge
├── mtproto.py        # MTProto utils
└── telegram_const.py # IP ranges
```

## ⚙️ Конфигурация

Создайте `.env`:

```env
PROXY_HOST=127.0.0.1
PROXY_PORT=1080
WS_POOL_SIZE=8
AUTH_ENABLED=true
AUTH_USERNAME=admin
AUTH_PASSWORD=secret
```

## 📜 Лицензия

MIT
