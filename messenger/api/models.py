# messenger/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class UserProfile(models.Model):
    """Профиль пользователя с дополнительными полями"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile', verbose_name=_('Пользователь'))
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name=_('Аватар'))
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

    def __str__(self):
        if self.type == self.PRIVATE:
            members = self.members.exclude(user=self.created_by)
            if members.exists():
                return f"Чат с {members.first().user.username}"
        return self.title or f"Группа {self.id}"


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
    """Вложения к сообщениям"""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments',
                                verbose_name=_('Сообщение'))
    file = models.FileField(upload_to='message_attachments/', verbose_name=_('Файл'))
    file_name = models.CharField(max_length=255, verbose_name=_('Имя файла'))
    file_size = models.BigIntegerField(verbose_name=_('Размер файла'))
    mime_type = models.CharField(max_length=100, verbose_name=_('Тип файла'))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата загрузки'))

    class Meta:
        db_table = 'message_attachments'
        verbose_name = _('Вложение сообщения')
        verbose_name_plural = _('Вложения сообщений')

    def __str__(self):
        return self.file_name