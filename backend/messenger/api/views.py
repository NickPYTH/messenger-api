from django.contrib.auth.models import User
from django.db.models import Q

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import *
from .utils import send_message, delete_message, update_message
from .models import *
from .serializers import (
    UserSerializer, ConversationSerializer,
    CreateConversationSerializer
)


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """Просмотр пользователей"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = User.objects.all()
        search_param = self.request.query_params.get('search', None)

        if search_param:
            # Ищем по полям User и связанным полям UserProfile
            queryset = queryset.filter(
                Q(username__icontains=search_param) |
                Q(email__icontains=search_param) |
                Q(first_name__icontains=search_param) |
                Q(last_name__icontains=search_param) |
                # Поля из UserProfile
                Q(profile__first_name__icontains=search_param) |
                Q(profile__last_name__icontains=search_param) |
                Q(profile__second_name__icontains=search_param) |
                Q(profile__staff__icontains=search_param) |
                Q(profile__filial__icontains=search_param) |
                Q(profile__email__icontains=search_param) |
                Q(profile__phone__icontains=search_param) |
                Q(profile__status__icontains=search_param)
            ).distinct()  # Добавляем distinct для исключения дубликатов

        return queryset


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


class CurrentUserViewSet(viewsets.ViewSet):
    """Текущий пользователь"""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class MessageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    # Добавляем поддержку multipart/form-data для загрузки файлов
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_serializer_class(self):
        """
        Динамический выбор сериализатора в зависимости от действия
        """
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
        queryset = Message.objects.filter(
            conversation__members__user=self.request.user
        ).select_related('sender', 'conversation').prefetch_related('attachments')

        # Опциональная фильтрация по conversation_id
        conversation_id = self.request.query_params.get('conversation_id')
        if conversation_id:
            queryset = queryset.filter(conversation_id=conversation_id)

        return queryset

    def create(self, request, *args, **kwargs):
        """
        Переопределяем метод create для обработки файлов
        """
        # Проверяем, есть ли файлы в запросе
        has_files = any(key.startswith('files') or key.startswith('attachments')
                        for key in request.FILES.keys())

        # Выбираем сериализатор в зависимости от наличия файлов
        if has_files:
            serializer_class = self.get_serializer_class()
        else:
            serializer_class = MessageSerializer

        serializer = serializer_class(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        try:
            self.perform_create(serializer)
        except Exception as e:
            return Response(
                {'error': f'Ошибка при создании сообщения: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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

    def perform_update(self, serializer):
        """
        Обновляем сообщение и отправляем через update_message
        """
        instance = serializer.save(sender=self.request.user)
        instance.is_edited = True
        instance.edited_at = timezone.now()
        instance.save()

        # TODO Обновляем время последнего изменения сообщения в беседе

        try:
            update_message(instance)
        except Exception as e:
            # Логируем ошибку, но не прерываем выполнение
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error update message via update_message: {str(e)}")


    def perform_create(self, serializer):
        """
        Сохраняем сообщение и отправляем через send_message
        """
        instance = serializer.save(sender=self.request.user)

        # TODO Обновляем время последнего сообщения в беседе
        # instance.conversation.last_message_at = instance.timestamp
        # instance.conversation.save(update_fields=['last_message_at'])

        # Отправляем сообщение
        try:
            send_message(instance)
        except Exception as e:
            # Логируем ошибку, но не прерываем выполнение
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error sending message via send_message: {str(e)}")

    def perform_destroy(self, instance):
        MessageAttachment.objects.filter(message=instance).delete()
        # Удаляем сообщение
        try:
            delete_message(instance)
        except Exception as e:
            # Логируем ошибку, но не прерываем выполнение
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error delete message via delete_message: {str(e)}")
        instance.delete()

    @action(detail=True, methods=['post'])
    def add_attachment(self, request, pk=None):
        """
        Добавление вложения к существующему сообщению
        """
        message = self.get_object()

        # Проверяем, что пользователь является отправителем сообщения
        if message.sender != request.user:
            return Response(
                {'error': 'Вы можете добавлять вложения только к своим сообщениям'},
                status=status.HTTP_403_FORBIDDEN
            )

        file_obj = request.FILES.get('file')
        if not file_obj:
            return Response(
                {'error': 'Не предоставлен файл'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Создаем вложение
            attachment = MessageAttachment(
                message=message,
                file=file_obj,
                file_name=file_obj.name,
                file_size=file_obj.size,
                mime_type=file_obj.content_type
            )
            attachment.save()

            # Обновляем время сообщения
            message.save()

            serializer = MessageAttachmentSerializer(
                attachment,
                context={'request': request}
            )

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f'Ошибка при добавлении вложения: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def attachments(self, request, pk=None):
        """
        Получение всех вложений сообщения
        """
        message = self.get_object()
        attachments = message.attachments.all()

        serializer = MessageAttachmentSerializer(
            attachments,
            many=True,
            context={'request': request}
        )

        return Response(serializer.data)


class MessageAttachmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для работы с вложениями сообщений
    """
    serializer_class = MessageAttachmentSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]  # Добавляем парсеры для загрузки

    def get_queryset(self):
        """
        Показываем только вложения из сообщений,
        где пользователь является участником беседы
        """
        queryset = MessageAttachment.objects.filter(
            message__conversation__members__user=self.request.user
        )

        # Опциональная фильтрация по message_id
        message_id = self.request.query_params.get('message_id')
        if message_id:
            queryset = queryset.filter(message_id=message_id)

        return queryset.select_related('message')

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Эндпоинт для скачивания файла
        Возвращает подписанный URL для скачивания с временем жизни
        """
        attachment = self.get_object()

        try:
            # Получаем подписанный URL с временем жизни (например, 5 минут)
            download_url = attachment.get_download_url(expires=300)

            # Альтернативно можно использовать прямое получение из storage
            if hasattr(attachment.file.storage, 'url'):
                download_url = attachment.file.storage.url(
                    attachment.file.name,
                    expires=300
                )

            return Response({
                'download_url': download_url,
                'file_name': attachment.file_name,
                'file_size': attachment.file_size,
                'mime_type': attachment.mime_type,
                'expires_in': 300  # Время жизни ссылки в секундах
            })

        except Exception as e:
            return Response(
                {'error': f'Не удалось получить ссылку для скачивания: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def preview(self, request, pk=None):
        """
        Эндпоинт для предпросмотра файла
        Возвращает URL для встраивания изображений/PDF
        """
        attachment = self.get_object()

        # Проверяем, можно ли предпросматривать файл
        if not (attachment.is_image or attachment.is_pdf):
            return Response(
                {'error': 'Предпросмотр не поддерживается для этого типа файла'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Генерируем URL с более длительным временем жизни для предпросмотра
        preview_url = attachment.get_download_url(expires=3600)  # 1 час

        return Response({
            'preview_url': preview_url,
            'type': 'image' if attachment.is_image else 'pdf',
            'file_name': attachment.file_name,
            'file_size': attachment.file_size,
            'mime_type': attachment.mime_type
        })

    @action(detail=False, methods=['post'])
    def upload(self, request):
        """
        Эндпоинт для загрузки файла без привязки к сообщению
        (полезно для предварительной загрузки)
        """
        file_obj = request.FILES.get('file')
        message_id = request.data.get('message_id')

        if not file_obj:
            return Response(
                {'error': 'Не предоставлен файл'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Создаем временное вложение
            attachment = MessageAttachment(
                file=file_obj,
                file_name=file_obj.name,
                file_size=file_obj.size,
                mime_type=file_obj.content_type
            )

            # Если указан message_id, привязываем
            if message_id:
                try:
                    message = Message.objects.get(
                        id=message_id,
                        conversation__members__user=request.user
                    )
                    attachment.message = message
                except Message.DoesNotExist:
                    return Response(
                        {'error': 'Сообщение не найдено или у вас нет доступа'},
                        status=status.HTTP_404_NOT_FOUND
                    )

            attachment.save()

            serializer = self.get_serializer(attachment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response(
                {'error': f'Ошибка при загрузке файла: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['delete'])
    def delete_file(self, request, pk=None):
        """
        Удаление вложения (и файла из MinIO)
        """
        attachment = self.get_object()

        # Проверяем права доступа
        # Пользователь может удалять вложения только из своих сообщений
        if attachment.message.sender != request.user:
            return Response(
                {'error': 'Вы можете удалять только вложения из своих сообщений'},
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            # Удаляем файл из MinIO и запись из БД
            attachment.delete()
            return Response(
                {'message': 'Файл успешно удален'},
                status=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            return Response(
                {'error': f'Ошибка при удалении файла: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FavoritesViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserFavoritesSerializer

    def get_queryset(self):
        return UserFavorite.objects.filter(user=self.request.user)
