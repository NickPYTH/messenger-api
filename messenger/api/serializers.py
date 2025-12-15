from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Conversation, ConversationMember, Message, MessageAttachment


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
    class Meta:
        model = MessageAttachment
        fields = ['id', 'file_name', 'file_size', 'mime_type', 'uploaded_at']


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    attachments = MessageAttachmentSerializer(many=True, read_only=True)
    sent_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', required=False, allow_null=True)
    edited_at = serializers.DateTimeField(format='%Y-%m-%d %H:%M:%S', required=False, allow_null=True)

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
        fields = ['type', 'title', 'member_ids']
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
