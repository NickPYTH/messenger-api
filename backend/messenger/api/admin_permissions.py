from django.contrib import admin
from django.contrib.auth.admin import UserAdmin


class RoleBasedModelAdmin(admin.ModelAdmin):
    """Базовый класс с ролевым доступом"""

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        # Поддержка видит только данные своего отдела
        if request.user.groups.filter(name='Поддержка мессенджера').exists():
            return self._filter_by_department(qs, request.user)

        # Аналитик видит все, но не может изменять
        if request.user.groups.filter(name='Аналитик мессенджера').exists():
            return qs

        return qs

    def has_add_permission(self, request):
        # Аналитик не может добавлять данные
        if request.user.groups.filter(name='Аналитик мессенджера').exists():
            return False
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        # Аналитик не может изменять данные
        if request.user.groups.filter(name='Аналитик мессенджера').exists():
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        # Только модераторы и админы могут удалять
        if request.user.groups.filter(name__in=['Поддержка мессенджера', 'Аналитик мессенджера']).exists():
            return False
        return super().has_delete_permission(request, obj)

    def _filter_by_department(self, qs, user):
        """Фильтрация по отделам (нужно адаптировать под вашу структуру)"""
        # Здесь можно реализовать логику фильтрации по отделам
        return qs


class CustomUserAdmin(UserAdmin, RoleBasedModelAdmin):
    """Кастомная админка пользователей с ролевым доступом"""

    def get_list_display(self, request):
        base_list_display = super().get_list_display(request)

        # Аналитики видят меньше информации
        if request.user.groups.filter(name='Аналитик мессенджера').exists():
            return ['username', 'email', 'first_name', 'last_name', 'is_active']

        return base_list_display

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        # Поддержка видит ограниченные поля
        if request.user.groups.filter(name='Поддержка мессенджера').exists():
            return (
                (None, {'fields': ('username', 'password')}),
                ('Персональная информация', {'fields': ('first_name', 'last_name', 'email')}),
                ('Статус', {'fields': ('is_active',)}),
            )

        return fieldsets