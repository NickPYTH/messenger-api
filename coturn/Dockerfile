# Используем официальный образ Coturn как основу
FROM coturn/coturn:latest

# Копируем наш основной файл конфигурации
COPY turnserver.conf /etc/coturn/turnserver.conf

# Копируем сертификаты TLS (опционально, если используете TLS)
# Предполагается, что сертификаты лежат в папке certs/ рядом с Dockerfile
# COPY certs/ /etc/coturn/certs/

# Открываем порты для STUN/TURN
# 3478 - стандартный порт для STUN/TURN (TCP/UDP)
# 5349 - стандартный порт для STUN/TURN over TLS (TCP)
# Диапазон портов 49152-65535 - для ретрансляции медиа (UDP)
EXPOSE 3478/tcp 3478/udp 5349/tcp 50000-50100/udp

# Указываем команду для запуска Coturn с нашим конфигом
CMD ["turnserver", "-c", "/etc/coturn/turnserver.conf"]