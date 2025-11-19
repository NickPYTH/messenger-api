from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class UserProfile(models.Model):
    """Профиль пользователя с дополнительными полями"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    status = models.CharField(max_length=100, default='В сети')
    last_seen = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Profile of {self.user.username}"


class Conversation(models.Model):
    """Модель беседы (чат)"""
    PRIVATE = 'private'
    GROUP = 'group'

    CONVERSATION_TYPES = [
        (PRIVATE, 'Private'),
        (GROUP, 'Group'),
    ]

    type = models.CharField(max_length=10, choices=CONVERSATION_TYPES, default=PRIVATE)
    title = models.CharField(max_length=255, null=True, blank=True)
    avatar = models.ImageField(upload_to='conversation_avatars/', null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'conversations'
        ordering = ['-last_message_at']


class ConversationMember(models.Model):
    """Участники беседы"""
    MEMBER = 'member'
    ADMIN = 'admin'

    ROLES = [
        (MEMBER, 'Member'),
        (ADMIN, 'Admin'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversation_memberships')
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='members')
    role = models.CharField(max_length=10, choices=ROLES, default=MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'conversation_members'
        unique_together = ['user', 'conversation']


class Message(models.Model):
    """Модель сообщения"""
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    text = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    edited_at = models.DateTimeField(null=True, blank=True)
    is_edited = models.BooleanField(default=False)

    class Meta:
        db_table = 'messages'
        ordering = ['sent_at']


class MessageAttachment(models.Model):
    """Вложения к сообщениям"""
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='message_attachments/')
    file_name = models.CharField(max_length=255)
    file_size = models.BigIntegerField()
    mime_type = models.CharField(max_length=100)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'message_attachments'