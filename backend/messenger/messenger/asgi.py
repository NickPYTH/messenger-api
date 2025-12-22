import os

from django.core.asgi import get_asgi_application

from api.consumers import MessagesConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'messenger.settings')

# Инициализируем Django перед импортом middleware
django_application = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from django.urls import path

# Импортируем middleware ПОСЛЕ инициализации Django
from api.middleware import WebSocketRemoteUserMiddleware

application = ProtocolTypeRouter({
    "http": django_application,
    "websocket": WebSocketRemoteUserMiddleware(
        AuthMiddlewareStack(
            URLRouter([
                path("messenger/ws/messages/", MessagesConsumer.as_asgi()),
            ])
        )
    ),
})
