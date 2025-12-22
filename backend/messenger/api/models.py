from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import os
from django.core.files.storage import default_storage


class UserProfile(models.Model):
    """Профиль пользователя с дополнительными полями"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name=_('Пользователь'))
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name=_('Аватар'))
    first_name = models.CharField(max_length=20, null=True, blank=True, verbose_name=_('Имя'))
    last_name = models.CharField(max_length=20, null=True, blank=True, verbose_name=_('Фамилия'))
    second_name = models.CharField(max_length=20, null=True, blank=True, verbose_name=_('Отчество'))
    staff = models.CharField(max_length=30, null=True, blank=True, verbose_name=_('Должность'))
    filial = models.CharField(max_length=30, null=True, blank=True, verbose_name=_('Филиал'))
    email = models.CharField(max_length=20, null=True, blank=True, verbose_name=_('Почта'))
    phone = models.CharField(max_length=20, null=True, blank=True, verbose_name=_('Телефон'))
    status = models.CharField(max_length=100, default='В сети', verbose_name=_('Статус'))
    last_seen = models.DateTimeField(default=timezone.now, verbose_name=_('Был в сети'))

    class Meta:
        db_table = 'users_profiles'
        verbose_name = _('Профиль пользователя')
        verbose_name_plural = _('Профили пользователей')

    def __str__(self):
        return f"Профиль {self.user.username}"


class Conversation(models.Model):
    """Модель беседы (чат)"""
    PRIVATE = 'private'
    GROUP = 'group'

    CONVERSATION_TYPES = [
        (PRIVATE, _('Личная')),
        (GROUP, _('Групповая')),
    ]

    type = models.CharField(max_length=10, choices=CONVERSATION_TYPES, default=PRIVATE, verbose_name=_('Тип беседы'))
    title = models.CharField(max_length=255, null=True, blank=True, verbose_name=_('Название'))
    avatar = models.ImageField(upload_to='conversation_avatars/', null=True, blank=True,
                               verbose_name=_('Аватар беседы'))
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_conversations',
                                   verbose_name=_('Создатель'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    last_message_at = models.DateTimeField(auto_now=True, verbose_name=_('Последнее сообщение'))

    class Meta:
        db_table = 'conversations'
        ordering = ['-last_message_at']
        verbose_name = _('Беседа')
        verbose_name_plural = _('Беседы')

    # messenger/models.py в классе Conversation

    def __str__(self):
        if self.type == self.PRIVATE:
            members = self.members.exclude(user=self.created_by)
            if members.exists():
                other_user = members.first().user
                # Пытаемся получить имя из профиля
                profile = getattr(other_user, 'profile', None)
                if profile and profile.first_name and profile.last_name:
                    return f"Чат с {profile.first_name} {profile.last_name}"
                return f"Чат с {other_user.username}"
            return "Личный чат"
        return self.title or f"Групповой чат #{self.id}"


class ConversationMember(models.Model):
    """Участники беседы"""
    MEMBER = 'member'
    ADMIN = 'admin'

    ROLES = [
        (MEMBER, _('Участник')),
        (ADMIN, _('Администратор')),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversation_memberships',
                             verbose_name=_('Пользователь'))
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='members',
                                     verbose_name=_('Беседа'))
    role = models.CharField(max_length=10, choices=ROLES, default=MEMBER, verbose_name=_('Роль'))
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата присоединения'))

    class Meta:
        db_table = 'conversation_members'
        unique_together = ['user', 'conversation']
        verbose_name = _('Участник беседы')
        verbose_name_plural = _('Участники бесед')

    def __str__(self):
        return f"{self.user.username} в {self.conversation}"


class Message(models.Model):
    """Модель сообщения"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages',
                                     verbose_name=_('Беседа'))
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages',
                               verbose_name=_('Отправитель'))
    text = models.TextField(verbose_name=_('Текст сообщения'))
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата отправки'))
    edited_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Дата редактирования'))
    is_edited = models.BooleanField(default=False, verbose_name=_('Отредактировано'))

    class Meta:
        db_table = 'messages'
        ordering = ['sent_at']
        verbose_name = _('Сообщение')
        verbose_name_plural = _('Сообщения')

    def __str__(self):
        return f"Сообщение от {self.sender.username}"


class MessageAttachment(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments',
                                verbose_name=_('Сообщение'))
    file = models.FileField(
        upload_to='message_attachments/Год %Y/Месяц %m/День %d/',  # Добавляем дату в путь
        verbose_name=_('Файл'),
        storage=default_storage  # Явно указываем storage
    )
    file_name = models.CharField(max_length=255, verbose_name=_('Имя файла'))
    file_size = models.BigIntegerField(verbose_name=_('Размер файла'))
    mime_type = models.CharField(max_length=100, verbose_name=_('Тип файла'))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата загрузки'))

    # Дополнительные поля для MinIO
    storage_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Путь в хранилище'),
        help_text=_('Полный путь к файлу в MinIO')
    )
    is_stored_in_minio = models.BooleanField(
        default=True,
        verbose_name=_('Хранится в MinIO'),
        help_text=_('Файл хранится в MinIO (True) или локально (False)')
    )

    class Meta:
        db_table = 'message_attachments'
        verbose_name = _('Вложение сообщения')
        verbose_name_plural = _('Вложения сообщений')

    def __str__(self):
        return self.file_name

    def save(self, *args, **kwargs):
        # Если это новый объект и есть файл
        if not self.pk and self.file:
            # Получаем оригинальное имя файла
            original_filename = self.file.name

            # Сохраняем информацию о файле
            if not self.file_name:
                # Извлекаем имя файла из пути
                self.file_name = os.path.basename(original_filename)

            if not self.mime_type:
                # Пробуем определить MIME тип
                import mimetypes
                mime_type, _ = mimetypes.guess_type(self.file_name)
                self.mime_type = mime_type or self.file.content_type or 'application/octet-stream'

            if not self.file_size:
                self.file_size = self.file.size

            # Сохраняем путь в хранилище
            # FileField сам вызовет storage.save() и обновит self.file.name
            # Мы сохраняем этот путь
            self.storage_path = self.file.name

            # Проверяем, используем ли мы MinIO storage
            from django.core.files.storage import default_storage
            self.is_stored_in_minio = hasattr(default_storage, 'bucket_name')

        super().save(*args, **kwargs)

    def get_file_url(self, request=None, expires=3600):
        """
        Возвращает URL для скачивания файла.
        Для MinIO генерирует подписанный URL с временем жизни.
        """
        if not self.file:
            return None

        try:
            # Если есть request, используем его для построения абсолютного URL
            if request:
                return request.build_absolute_uri(self.file.url)

            # Иначе возвращаем URL от storage
            url = self.file.url

            # Для MinIO можно дополнительно настроить время жизни URL
            if hasattr(self.file.storage, 'url') and callable(self.file.storage.url):
                # Используем метод storage для получения URL
                return url

            return url

        except Exception as e:
            # Логируем ошибку, но не падаем
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error generating URL for file {self.file.name}: {str(e)}")
            return None

    def get_download_url(self, expires=3600):
        """
        Альтернативный метод для получения подписанного URL с кастомным временем жизни
        """
        if not self.file:
            return None

        try:
            # Пробуем использовать подписанные URL если storage поддерживает
            if hasattr(self.file.storage, 'get_presigned_url'):
                return self.file.storage.get_presigned_url(
                    self.storage_path,
                    expires=expires
                )

            # Иначе стандартный URL
            return self.file.url

        except Exception:
            return self.file.url

    def delete(self, *args, **kwargs):
        """
        Удаляет файл из хранилища при удалении объекта
        """
        # Удаляем файл из хранилища
        if self.file:
            self.file.delete(save=False)

        # Удаляем сам объект
        super().delete(*args, **kwargs)

    @property
    def file_extension(self):
        """Возвращает расширение файла"""
        if self.file_name:
            return os.path.splitext(self.file_name)[1].lower()
        return ''

    @property
    def is_image(self):
        """Проверяет, является ли файл изображением"""
        return self.mime_type and self.mime_type.startswith('image/')

    @property
    def is_video(self):
        """Проверяет, является ли файл видео"""
        return self.mime_type and self.mime_type.startswith('video/')

    @property
    def is_audio(self):
        """Проверяет, является ли файл аудио"""
        return self.mime_type and self.mime_type.startswith('audio/')

    @property
    def is_pdf(self):
        """Проверяет, является ли файл PDF"""
        return self.mime_type == 'application/pdf'

    @property
    def human_readable_size(self):
        """Возвращает размер файла в читаемом формате"""
        if not self.file_size:
            return "0 B"

        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"
