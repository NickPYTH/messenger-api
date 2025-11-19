from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q


class RoleManager:
    """Менеджер для создания и настройки ролей"""

    ROLES = {
        'messenger_support': 'Поддержка мессенджера',
        'messenger_moderator': 'Модератор мессенджера',
        'messenger_analyst': 'Аналитик мессенджера',
        'department_admin': 'Администратор отдела',
    }

    @classmethod
    def setup_roles(cls):
        """Создание ролей с соответствующими правами"""
        for codename, name in cls.ROLES.items():
            group, created = Group.objects.get_or_create(
                name=name,
                defaults={'name': name}
            )
            cls._assign_permissions(group, codename)

    @classmethod
    def _assign_permissions(cls, group, role_codename):
        """Назначение прав для каждой роли"""
        permissions = cls._get_role_permissions(role_codename)
        group.permissions.set(permissions)

    @classmethod
    def _get_role_permissions(cls, role_codename):
        """Получение списка прав для роли"""
        content_types = ContentType.objects.filter(
            Q(app_label='messenger') |
            Q(app_label='auth', model='user') |
            Q(app_label='auth', model='group')
        )

        base_permissions = Permission.objects.filter(content_type__in=content_types)

        role_permissions = {
            'messenger_support': base_permissions.filter(
                codename__in=['view_user', 'view_conversation', 'view_message']
            ),
            'messenger_moderator': base_permissions.filter(
                Q(codename__startswith='view_') |
                Q(codename__startswith='delete_') |
                Q(codename__in=['change_message', 'change_conversation'])
            ),
            'messenger_analyst': base_permissions.filter(
                codename__startswith='view_'
            ),
            'department_admin': base_permissions.filter(
                Q(codename__startswith='view_') |
                Q(codename__in=['add_user', 'change_user', 'add_conversation', 'change_conversation'])
            ),
        }

        return role_permissions.get(role_codename, base_permissions.none())