from storages.backends.s3 import S3Storage
from django.conf import settings
import mimetypes


class CustomMinIOStorage(S3Storage):
    """
    Кастомный storage для MinIO с дополнительными возможностями
    """

    def _save(self, name, content):
        """
        Переопределяем сохранение для добавления метаданных
        """
        # Определяем Content-Type если не указан
        if not hasattr(content, 'content_type') or not content.content_type:
            content_type, _ = mimetypes.guess_type(name)
            if content_type:
                content.content_type = content_type

        # Сохраняем файл
        saved_name = super()._save(name, content)

        return saved_name

    def get_presigned_url(self, name, expires=3600, response_headers=None):
        """
        Генерирует подписанный URL с дополнительными параметрами
        """
        try:
            # Используем клиент boto3 для генерации подписанного URL
            client = self.connection.meta.client

            params = {
                'Bucket': self.bucket_name,
                'Key': name,
                'Expires': expires
            }

            # Добавляем заголовки для скачивания
            if response_headers:
                params['ResponseHeaders'] = response_headers

            # Генерируем URL
            url = client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expires
            )

            return url

        except Exception as e:
            # Если не удалось, возвращаем обычный URL
            return self.url(name)

    def generate_public_url(self, name):
        """
        Генерирует публичный URL (если файл имеет public-read ACL)
        """
        return f"{self.endpoint_url}/{self.bucket_name}/{name}"