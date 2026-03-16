# CS3NEWS GIGAVPN

Внутренняя инфраструктурная утилита CS3NEWS для оптимизации сетевой связности.

## Назначение

Локальный SOCKS5-прокси для ускорения внутренних коммуникаций через WebSocket-туннелирование. Используется командой для стабилизации соединений с внешними API и сервисами.

## Быстрый старт

```bash
# Установка
curl -fsSL https://raw.githubusercontent.com/QUALITY-SUPREMACY/cs3news-gigavpn/main/install.sh | bash

# Запуск
cs3news-gigavpn
```

## Конфигурация

Файл `.env`:

```env
PROXY_HOST=127.0.0.1
PROXY_PORT=1080
WS_POOL_SIZE=8
LOG_LEVEL=INFO
```

## Архитектура

```
proxy/
├── main.py           # Точка входа
├── config.py         # Конфигурация
├── socks5.py         # SOCKS5 протокол
├── rate_limiter.py   # Rate limiting
├── pool.py           # Пул соединений
├── websocket.py      # WebSocket layer
├── bridge.py         # Мост трафика
├── mtproto.py        # Протокольные утилиты
└── telegram_const.py # Константы сети
```

## Безопасность

- Certificate pinning
- Rate limiting
- Graceful shutdown
- Thread-safe операции

## Лицензия

Внутреннее ПО CS3NEWS. Все права защищены.