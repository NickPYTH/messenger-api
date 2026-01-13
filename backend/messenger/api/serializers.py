import os

from django.contrib.auth.models import User
from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError


from .models import Conversation, ConversationMember, Message, MessageAttachment, UserFavorite


class UserSerializer(serializers.ModelSerializer):
    profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile']

    def get_profile(self, obj):
        profile = getattr(obj, 'profile', None)
        if profile:
            return {
                'avatar': profile.avatar.url if profile.avatar else None,
                'first_name': profile.first_name,
                'last_name': profile.last_name,
                'second_name': profile.second_name,
                'staff': profile.staff,
                'filial': profile.filial,
                'phone': profile.phone,
                'status': profile.status,
                'last_seen': profile.last_seen.strftime('%d-%m-%Y %H:%M') if profile.last_seen is not None else None
            }
        return None


class ConversationMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = ConversationMember
        fields = ['id', 'user', 'role', 'joined_at']


class MessageAttachmentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    file_name = serializers.CharField(read_only=True)
    file_extension = serializers.SerializerMethodField()
    human_readable_size = serializers.SerializerMethodField()
    file_type = serializers.SerializerMethodField()  # 'image', 'video', 'pdf', etc.

    # Поля для загрузки (только для создания)
    file = serializers.FileField(write_only=True, required=False)
    file_content = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = MessageAttachment
        fields = [
            'id',
            'file_name',
            'file_size',
            'human_readable_size',
            'mime_type',
            'file_extension',
            'file_type',
            'uploaded_at',
            'file_url',
            'download_url',
            'is_stored_in_minio',
            'file',  # write-only
            'file_content'  # write-only (для base64)
        ]
        read_only_fields = [
            'id', 'file_name', 'file_size', 'mime_type',
            'uploaded_at', 'is_stored_in_minio', 'file_extension',
            'human_readable_size', 'file_type'
        ]

    def get_file_url(self, obj):
        """
        Возвращает URL для доступа к файлу
        """
        url = obj.file.url if obj.file else None

        if url and url.startswith('https://'):
            # Заменяем https на http
            url = url.replace('https://', 'http://', 1)

        return url

    def get_download_url(self, obj):
        """
        Возвращает URL для скачивания файла с временем жизни
        """
        # Можно задать разное время жизни для разных типов файлов
        expires = 3600  # 1 час по умолчанию

        # Для изображений - дольше
        if obj.is_image:
            expires = 86400  # 24 часа

        return obj.get_download_url(expires=expires)

    def get_file_extension(self, obj):
        return obj.file_extension

    def get_human_readable_size(self, obj):
        return obj.human_readable_size

    def get_file_type(self, obj):
        """Определяет тип файла для фронтенда"""
        if obj.is_image:
            return 'image'
        elif obj.is_video:
            return 'video'
        elif obj.is_audio:
            return 'audio'
        elif obj.is_pdf:
            return 'pdf'
        elif obj.mime_type and 'text/' in obj.mime_type:
            return 'text'
        elif obj.mime_type and 'application/' in obj.mime_type:
            # Определяем тип приложения
            if 'word' in obj.mime_type or 'doc' in obj.mime_type:
                return 'word'
            elif 'excel' in obj.mime_type or 'sheet' in obj.mime_type:
                return 'excel'
            elif 'powerpoint' in obj.mime_type or 'presentation' in obj.mime_type:
                return 'powerpoint'
            elif 'zip' in obj.mime_type or 'compressed' in obj.mime_type:
                return 'archive'
            else:
                return 'document'
        else:
            return 'file'

    def validate_file(self, value):
        """
        Валидация загружаемого файла
        """
        # Максимальный размер файла (например, 10MB)
        max_size = 10 * 1024 * 1024  # 10 MB

        if value.size > max_size:
            raise serializers.ValidationError(
                f"Файл слишком большой. Максимальный размер: {max_size // (1024 * 1024)}MB"
            )

        # Проверяем разрешенные MIME типы
        allowed_types = [
            'image/jpeg', 'image/png', 'image/gif', 'image/webp',
            'application/pdf',
            'text/plain', 'text/csv',
            'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.ms-powerpoint',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/zip',
            'audio/mpeg', 'audio/wav',
            'video/mp4', 'video/webm',
        ]

        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                f"Тип файла {value.content_type} не поддерживается"
            )

        return value

    def create(self, validated_data):
        """
        Создание вложения с файлом
        """
        # Извлекаем файл из validated_data
        file_obj = validated_data.pop('file', None)
        file_content = validated_data.pop('file_content', None)

        if not file_obj and not file_content:
            raise serializers.ValidationError(
                "Необходимо предоставить файл или содержимое файла"
            )

        # Создаем объект вложения
        attachment = MessageAttachment(**validated_data)

        if file_obj:
            # Используем переданный файл
            attachment.file = file_obj
        elif file_content:
            # Обработка base64 контента (если нужно)
            import base64
            from django.core.files.base import ContentFile

            # Декодируем base64
            format, file_str = file_content.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(
                base64.b64decode(file_str),
                name=f"attachment_{validated_data.get('file_name', 'file')}.{ext}"
            )
            attachment.file = data

        # Сохраняем объект (автоматически сохранит файл в MinIO)
        attachment.save()

        return attachment

    def _get_file_icon(self, file_type):
        """Возвращает иконку для типа файла"""
        icons = {
            'image': '🖼️',
            'video': '🎬',
            'audio': '🎵',
            'pdf': '📄',
            'text': '📝',
            'word': '📄',
            'excel': '📊',
            'powerpoint': '📊',
            'archive': '📦',
            'document': '📄',
            'file': '📎'
        }
        return icons.get(file_type, '📎')


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    sent_at = serializers.DateTimeField(format='%d.%m.%Y %H:%M', required=False, allow_null=True)
    edited_at = serializers.DateTimeField(format='%d.%m.%Y %H:%M', required=False, allow_null=True)

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'text', 'attachments', 'sent_at', 'edited_at', 'is_edited']


class ConversationSerializer(serializers.ModelSerializer):
    members = ConversationMemberSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'type', 'title', 'avatar', 'created_by', 'members', 'last_message', 'created_at',
                  'last_message_at']

    def get_last_message(self, obj):
        last_message = obj.messages.last()
        if last_message:
            return MessageSerializer(last_message).data
        return None


class CreateConversationSerializer(serializers.ModelSerializer):
    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        min_length=1,
        max_length=50  # ограничение на максимальное количество участников
    )

    class Meta:
        model = Conversation
        fields = ['id', 'type', 'title', 'member_ids']
        extra_kwargs = {
            'title': {'required': False, 'allow_blank': True}
        }

    def validate(self, data):
        """
        Валидация данных при создании беседы
        """
        request = self.context.get('request')
        member_ids = data.get('member_ids', [])
        conversation_type = data.get('type', Conversation.PRIVATE)

        # Проверяем, что пользователь не добавляет себя
        if request and request.user.is_authenticated:
            user_id = request.user.id
            if user_id in member_ids:
                raise serializers.ValidationError({
                    'member_ids': 'Нельзя добавлять себя в список участников'
                })

        # Для личных чатов
        if conversation_type == Conversation.PRIVATE:
            # Проверяем количество участников
            if len(member_ids) != 1:
                raise serializers.ValidationError({
                    'member_ids': 'Личный чат может быть создан только с одним участником'
                })

            # Проверяем, существует ли уже такой личный чат
            if request and request.user.is_authenticated:
                other_user_id = member_ids[0]

                # Ищем существующие личные чаты между пользователями
                existing_conversation = self._find_existing_private_chat(
                    request.user.id,
                    other_user_id
                )

                if existing_conversation:
                    # Возвращаем существующий чат вместо создания нового
                    raise serializers.ValidationError({
                        'detail': f'Личный чат уже существует (ID: {existing_conversation.id})',
                        'existing_conversation_id': existing_conversation.id
                    })

        # Для групповых чатов
        elif conversation_type == Conversation.GROUP:
            # Проверяем, что указано название
            if not data.get('title'):
                raise serializers.ValidationError({
                    'title': 'Для группового чата необходимо указать название'
                })

            # Проверяем минимальное количество участников
            if len(member_ids) < 2:
                raise serializers.ValidationError({
                    'member_ids': 'Групповой чат должен содержать минимум 2 участника (кроме создателя)'
                })

        # Проверяем, что все пользователи существуют
        self._validate_user_ids(member_ids)

        return data

    def _validate_user_ids(self, member_ids):
        """
        Проверяем, что все переданные ID пользователей существуют
        """
        from django.contrib.auth.models import User

        existing_ids = set(User.objects.filter(
            id__in=member_ids
        ).values_list('id', flat=True))

        missing_ids = set(member_ids) - existing_ids

        if missing_ids:
            raise serializers.ValidationError({
                'member_ids': f'Пользователи с ID {list(missing_ids)} не найдены'
            })

    def _find_existing_private_chat(self, user1_id, user2_id):
        """
        Ищет существующий личный чат между двумя пользователями
        """
        from django.contrib.auth.models import User
        from .models import ConversationMember

        try:
            # Находим все личные чаты, где есть user1
            user1_chats = ConversationMember.objects.filter(
                user_id=user1_id,
                conversation__type=Conversation.PRIVATE
            ).values_list('conversation_id', flat=True)

            # Проверяем, есть ли в этих чатах user2
            existing_member = ConversationMember.objects.filter(
                user_id=user2_id,
                conversation_id__in=user1_chats,
                conversation__type=Conversation.PRIVATE
            ).first()

            if existing_member:
                return existing_member.conversation
        except Exception:
            return None

        return None

    def create(self, validated_data):
        member_ids = validated_data.pop('member_ids')
        request = self.context.get('request')

        # Автоматически определяем тип, если не указан явно
        conversation_type = validated_data.get('type')
        if not conversation_type:
            # Если 1 участник - личный чат, иначе - групповой
            validated_data['type'] = Conversation.PRIVATE if len(member_ids) == 1 else Conversation.GROUP

        # Для личных чатов убираем название (оно генерируется автоматически)
        if validated_data.get('type') == Conversation.PRIVATE:
            validated_data.pop('title', None)

        # Создаем беседу
        conversation = Conversation.objects.create(
            **validated_data,
        )

        # Добавляем создателя как администратора
        if request and request.user.is_authenticated:
            ConversationMember.objects.create(
                user=request.user,
                conversation=conversation,
                role=ConversationMember.ADMIN
            )

        # Добавляем остальных участников
        from django.contrib.auth.models import User
        users = User.objects.filter(id__in=member_ids)

        for user in users:
            ConversationMember.objects.create(
                user=user,
                conversation=conversation,
                role=ConversationMember.MEMBER
            )

        # Для личных чатов генерируем автоматическое название
        if conversation.type == Conversation.PRIVATE and not conversation.title:
            members = conversation.members.exclude(user=conversation.created_by)
            if members.exists():
                other_user = members.first().user
                # Используем полное имя, если доступно
                profile = getattr(other_user, 'profile', None)
                if profile and profile.first_name and profile.last_name:
                    conversation.title = f"{profile.first_name} {profile.last_name}"
                else:
                    conversation.title = other_user.username
                conversation.save()

        return conversation


class CreateMessageWithFilesSerializer(serializers.ModelSerializer):
    files = serializers.ListField(
        child=serializers.FileField(
            max_length=100 * 1024 * 1024,
            allow_empty_file=False
        ),
        write_only=True,
        required=False
    )

    class Meta:
        model = Message
        fields = ['conversation', 'text', 'files']

    def validate(self, data):
        request = self.context.get('request')
        conversation = data.get('conversation')
        files = data.get('files', [])
        text = data.get('text', '')

        if not text and not files:
            raise serializers.ValidationError('Сообщение должно содержать текст или файл')

        return data

    def create(self, validated_data):
        files = validated_data.pop('files', [])

        # ВАЖНО: sender НЕ передаем здесь
        # Он будет передан через serializer.save(sender=request.user) в perform_create
        message = Message.objects.create(**validated_data)

        for file_obj in files:
            MessageAttachment.objects.create(
                message=message,
                file=file_obj,
                file_name=file_obj.name,
                file_size=file_obj.size,
                mime_type=file_obj.content_type or 'application/octet-stream'
            )

        return message

class UserFavoritesSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    friend = UserSerializer(read_only=True)

    def validate(self, data):
        return self.initial_data

    def create(self, validated_data):
        friend = User.objects.get(id=validated_data.get('friend').get('id'))
        favorite = UserFavorite.objects.create(user=self.context['request'].user,friend=friend)
        return favorite

    class Meta:
        model = UserFavorite
        fields = '__all__'


