# messenger/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import UserProfile, Conversation, ConversationMember, Message, MessageAttachment


# === РАСШИРЕНИЕ СТАНДАРТНОЙ МОДЕЛИ USER ===
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name = _('Профиль')
    verbose_name_plural = _('Данные профиля')
    fields = ['avatar', 'phone', 'status', 'last_seen']
    readonly_fields = ['last_seen']


class CustomUserAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'get_status', 'get_last_seen', 'is_staff']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'profile__status']
    search_fields = ['username', 'email', 'first_name', 'last_name', 'profile__status']
    inlines = [UserProfileInline]
    list_per_page = 50

    def get_status(self, obj):
        return obj.profile.status if hasattr(obj, 'profile') else 'Нет профиля'

    get_status.short_description = _('Статус')

    def get_last_seen(self, obj):
        return obj.profile.last_seen if hasattr(obj, 'profile') else 'Неизвестно'

    get_last_seen.short_description = _('Был в сети')


# Перерегистрируем User с кастомной админкой
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)


# === МОДЕЛЬ USERPROFILE ===
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'status', 'last_seen', 'avatar_preview']
    list_filter = ['status', 'last_seen']
    search_fields = ['user__username', 'user__email', 'phone', 'status']
    readonly_fields = ['last_seen', 'avatar_preview']
    list_per_page = 50

    def avatar_preview(self, obj):
        if obj.avatar:
            return format_html('<img src="{}" width="50" height="50" style="border-radius: 50%;" />', obj.avatar.url)
        return _("Нет аватара")

    avatar_preview.short_description = _('Аватар')


# === INLINE ДЛЯ УЧАСТНИКОВ БЕСЕДЫ ===
class ConversationMemberInline(admin.TabularInline):
    model = ConversationMember
    extra = 1
    verbose_name = _('Участник')
    verbose_name_plural = _('Участники беседы')
    raw_id_fields = ['user']
    autocomplete_fields = ['user']


# === INLINE ДЛЯ СООБЩЕНИЙ ===
class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    verbose_name = _('Сообщение')
    verbose_name_plural = _('Сообщения в беседе')
    readonly_fields = ['sent_at', 'is_edited']
    fields = ['sender', 'text', 'sent_at', 'is_edited']
    raw_id_fields = ['sender']
    autocomplete_fields = ['sender']


# === МОДЕЛЬ CONVERSATION ===
@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'type', 'title', 'created_by', 'members_count', 'messages_count', 'last_message_at',
                    'created_at']
    list_filter = ['type', 'created_at', 'last_message_at']
    search_fields = ['title', 'created_by__username', 'members__user__username']
    readonly_fields = ['created_at', 'last_message_at', 'members_count_display', 'messages_count_display']
    list_select_related = ['created_by']
    list_per_page = 50
    inlines = [ConversationMemberInline, MessageInline]

    fieldsets = (
        (_('Основная информация'), {
            'fields': ('type', 'title', 'avatar', 'created_by')
        }),
        (_('Даты'), {
            'fields': ('created_at', 'last_message_at')
        }),
        (_('Статистика'), {
            'fields': ('members_count_display', 'messages_count_display')
        }),
    )

    def members_count(self, obj):
        return obj.members.count()

    members_count.short_description = _('Участников')

    def messages_count(self, obj):
        return obj.messages.count()

    messages_count.short_description = _('Сообщений')

    def members_count_display(self, obj):
        return obj.members.count()

    members_count_display.short_description = _('Количество участников')

    def messages_count_display(self, obj):
        return obj.messages.count()

    messages_count_display.short_description = _('Количество сообщений')


# === МОДЕЛЬ CONVERSATIONMEMBER ===
@admin.register(ConversationMember)
class ConversationMemberAdmin(admin.ModelAdmin):
    list_display = ['user', 'conversation', 'role', 'joined_at']
    list_filter = ['role', 'joined_at', 'conversation__type']
    search_fields = ['user__username', 'conversation__title']
    raw_id_fields = ['user', 'conversation']
    list_select_related = ['user', 'conversation']
    list_per_page = 100


# === INLINE ДЛЯ ВЛОЖЕНИЙ ===
class MessageAttachmentInline(admin.TabularInline):
    model = MessageAttachment
    extra = 0
    verbose_name = _('Вложение')
    verbose_name_plural = _('Вложения к сообщению')
    readonly_fields = ['file_size', 'mime_type', 'uploaded_at']
    fields = ['file', 'file_name', 'file_size', 'mime_type', 'uploaded_at']


# === МОДЕЛЬ MESSAGE ===
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'sender', 'text_preview', 'sent_at', 'is_edited', 'attachments_count']
    list_filter = ['sent_at', 'is_edited', 'conversation__type']
    search_fields = ['text', 'sender__username', 'conversation__title']
    readonly_fields = ['sent_at', 'edited_at', 'is_edited']
    raw_id_fields = ['conversation', 'sender']
    list_select_related = ['conversation', 'sender']
    list_per_page = 50
    inlines = [MessageAttachmentInline]

    fieldsets = (
        (_('Основная информация'), {
            'fields': ('conversation', 'sender', 'text')
        }),
        (_('Даты и статусы'), {
            'fields': ('sent_at', 'edited_at', 'is_edited')
        }),
    )

    def text_preview(self, obj):
        if len(obj.text) > 50:
            return f"{obj.text[:50]}..."
        return obj.text

    text_preview.short_description = _('Текст сообщения')

    def attachments_count(self, obj):
        return obj.attachments.count()

    attachments_count.short_description = _('Вложений')


# === МОДЕЛЬ MESSAGEATTACHMENT ===
@admin.register(MessageAttachment)
class MessageAttachmentAdmin(admin.ModelAdmin):
    list_display = ['file_name', 'message', 'file_size', 'mime_type', 'uploaded_at']
    list_filter = ['mime_type', 'uploaded_at']
    search_fields = ['file_name', 'message__text', 'message__sender__username']
    readonly_fields = ['file_size', 'mime_type', 'uploaded_at', 'file_preview']
    list_select_related = ['message']
    list_per_page = 50

    fieldsets = (
        (_('Информация о файле'), {
            'fields': ('file', 'file_name', 'file_size', 'mime_type')
        }),
        (_('Связанное сообщение'), {
            'fields': ('message',)
        }),
        (_('Даты'), {
            'fields': ('uploaded_at',)
        }),
        (_('Предпросмотр'), {
            'fields': ('file_preview',)
        }),
    )

    def file_preview(self, obj):
        if obj.file:
            if obj.mime_type and obj.mime_type.startswith('image/'):
                return format_html('<img src="{}" width="200" />', obj.file.url)
            return format_html('<a href="{}" target="_blank">Открыть файл</a>', obj.file.url)
        return _("Файл не загружен")

    file_preview.short_description = _('Предпросмотр')


# === КАСТОМНЫЙ ЗАГОЛОВОК АДМИНКИ ===
admin.site.site_header = _("Панель управления корпоративным мессенджером")
admin.site.site_title = _("Администрирование мессенджера")
admin.site.index_title = _("Управление данными мессенджера")