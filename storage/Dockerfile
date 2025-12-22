FROM minio/minio:latest

# Создаем директории для данных
RUN mkdir -p /data/minio

# Открываем порты
EXPOSE 9000 9001

# Переменные окружения
ENV MINIO_ROOT_USER=minioadmin
ENV MINIO_ROOT_PASSWORD=minioadminpassword
ENV MINIO_REGION=us-east-1
ENV MINIO_DOMAIN=localhost
ENV MINIO_BROWSER=on

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9000/minio/health/live || exit 1

# Запускаем MinIO сервер
CMD ["minio", "server", "/data", "--console-address", ":9001"]