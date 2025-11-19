# messenger/management/commands/setup_roles.py
import os
import django
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q


class Command(BaseCommand):
    help = 'Создает стандартные роли для мессенджера'

    def handle(self, *args, **options):
        # Создаем группы/роли
        roles = {
            'Поддержка мессенджера': ['view_user', 'view_conversation', 'view_message'],
            'Модератор мессенджера': [
                'view_user', 'view_conversation', 'view_message',
                'delete_conversation', 'delete_message', 'change_message', 'change_conversation'
            ],
            'Аналитик мессенджера': ['view_user', 'view_conversation', 'view_message'],
            'Администратор отдела': [
                'view_user', 'view_conversation', 'view_message',
                'add_user', 'change_user', 'add_conversation', 'change_conversation'
            ],
        }

        for role_name, permissions in roles.items():
            group, created = Group.objects.get_or_create(name=role_name)

            # Находим права доступа
            content_types = ContentType.objects.filter(
                Q(app_label='messenger') |
                Q(app_label='auth', model='user')
            )

            perms = Permission.objects.filter(
                content_type__in=content_types,
                codename__in=permissions
            )

            group.permissions.set(perms)

            if created:
                self.stdout.write(self.style.SUCCESS(f'Создана роль: {role_name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Обновлена роль: {role_name}'))

        self.stdout.write(self.style.SUCCESS('Все роли успешно созданы!'))