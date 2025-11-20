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
                'last_seen': profile.last_seen
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
        write_only=True
    )

    class Meta:
        model = Conversation
        fields = ['type', 'title', 'member_ids']

    def create(self, validated_data):
        member_ids = validated_data.pop('member_ids')
        conversation = Conversation.objects.create(**validated_data)

        # Добавляем создателя в участники
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            ConversationMember.objects.create(
                user=request.user,
                conversation=conversation,
                role=ConversationMember.ADMIN
            )

        # Добавляем остальных участников
        for user_id in member_ids:
            user = User.objects.get(id=user_id)
            ConversationMember.objects.create(
                user=user,
                conversation=conversation,
                role=ConversationMember.MEMBER
            )

        return conversation# messenger/serializers.py
from rest_framework import serializers
from django.contrib.auth.models import User
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
                'last_seen': profile.last_seen
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

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'text', 'attachments', 'sent_at', 'edited_at', 'is_edited']

class ConversationSerializer(serializers.ModelSerializer):
    members = ConversationMemberSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'type', 'title', 'avatar', 'created_by', 'members', 'last_message', 'created_at', 'last_message_at']

    def get_last_message(self, obj):
        last_message = obj.messages.last()
        if last_message:
            return MessageSerializer(last_message).data
        return None

class CreateConversationSerializer(serializers.ModelSerializer):
    member_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True
    )

    class Meta:
        model = Conversation
        fields = ['type', 'title', 'member_ids']

    def create(self, validated_data):
        member_ids = validated_data.pop('member_ids')
        conversation = Conversation.objects.create(**validated_data)

        # Добавляем создателя в участники
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            ConversationMember.objects.create(
                user=request.user,
                conversation=conversation,
                role=ConversationMember.ADMIN
            )

        # Добавляем остальных участников
        for user_id in member_ids:
            user = User.objects.get(id=user_id)
            ConversationMember.objects.create(
                user=user,
                conversation=conversation,
                role=ConversationMember.MEMBER
            )

        return conversation