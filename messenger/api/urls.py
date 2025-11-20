from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.UserViewSet, basename='users')
router.register(r'conversations', views.ConversationViewSet, basename='conversations')
router.register(r'messages', views.MessageViewSet, basename='messages')
router.register(r'me', views.CurrentUserViewSet, basename='current-user')

urlpatterns = [
    path('', include(router.urls)),
]