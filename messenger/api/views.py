from datetime import timezone

from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Conversation, Message, MessageAttachment
from .serializers import (
    UserSerializer, ConversationSerializer,
    MessageSerializer, CreateConversationSerializer, MessageAttachmentSerializer
)
from .utils import send_message


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """Просмотр пользователей"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return User.objects.all()


class ConversationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Conversation.objects.filter(
            members__user=self.request.user
        ).distinct()

    def get_serializer_class(self):
        if self.action == 'create':
            return CreateConversationSerializer
        return ConversationSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        Message.objects.filter(conversation=instance).delete()
        instance.delete()

    @action(detail=True, methods=['get'])
    def messages(self, request, pk=None):
        conversation = self.get_object()
        messages = conversation.messages.all()
        serializer = MessageSerializer(messages, many=True)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # Добавляем поддержку multipart/form-data для загрузки файлов
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        """
        Динамический выбор сериализатора в зависимости от действия
        """
        from .serializers import MessageSerializer, CreateMessageWithFilesSerializer

        if self.action == 'create':
            # Определяем по content-type, какой сериализатор использовать
            if self.request and hasattr(self.request, 'content_type'):
                content_type = self.request.content_type
                if content_type and 'multipart/form-data' in content_type:
                    # Если загружаются файлы
                    return CreateMessageWithFilesSerializer
            # Для JSON запросов используем обычный сериализатор
            return MessageSerializer
        elif self.action in ['update', 'partial_update']:
            # При обновлении используем обычный сериализатор
            return MessageSerializer
        else:
            # Для чтения и других действий
            return MessageSerializer

    def get_queryset(self):
        """
        Получаем только сообщения из бесед, где пользователь является участником
        """
        return Message.objects.filter(
            conversation__members__user=self.request.user
        ).select_related('sender', 'conversation').prefetch_related('attachments')

    def create(self, request, *args, **kwargs):
        """
        Переопределяем метод create для обработки файлов
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # После создания возвращаем данные в формате основного сериализатора
        message = serializer.instance
        response_serializer = MessageSerializer(
            message,
            context={'request': request}
        )

        headers = self.get_success_headers(response_serializer.data)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def perform_create(self, serializer):
        """
        Сохраняем сообщение и отправляем через send_message
        """
        instance = serializer.save(sender=self.request.user)
        # Отправляем сообщение (предполагается, что send_message уже реализована)
        send_message(instance)

    def update(self, request, *args, **kwargs):
        """
        Обновление сообщения (только текст)
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Проверяем, что пользователь является отправителем
        if instance.sender != request.user:
            return Response(
                {'detail': 'Вы можете редактировать только свои сообщения'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Для обновления используем MessageSerializer (без поддержки файлов)
        serializer = MessageSerializer(
            instance,
            data=request.data,
            partial=partial,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        # Устанавливаем флаг редактирования
        if 'text' in request.data and request.data['text'] != instance.text:
            serializer.validated_data['is_edited'] = True
            serializer.validated_data['edited_at'] = timezone.now()

        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)


class CurrentUserViewSet(viewsets.ViewSet):
    """Текущий пользователь"""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class MessageAttachmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для получения информации о вложениях
    """
    queryset = MessageAttachment.objects.all()
    serializer_class = MessageAttachmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Показываем только вложения из сообщений,
        где пользователь является участником беседы
        """
        return MessageAttachment.objects.filter(
            message__conversation__members__user=self.request.user
        )