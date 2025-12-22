from django.contrib import admin


class ConversationTypeFilter(admin.SimpleListFilter):
    title = 'Тип беседы'
    parameter_name = 'type'

    def lookups(self, request, model_admin):
        return [
            ('private', 'Личные'),
            ('group', 'Групповые'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'private':
            return queryset.filter(type='private')
        if self.value() == 'group':
            return queryset.filter(type='group')
        return queryset# messenger/filters.py
from django.contrib import admin

class ConversationTypeFilter(admin.SimpleListFilter):
    title = 'Тип беседы'
    parameter_name = 'type'

    def lookups(self, request, model_admin):
        return [
            ('private', 'Личные'),
            ('group', 'Групповые'),
        ]

    def queryset(self, request, queryset):
        if self.value() == 'private':
            return queryset.filter(type='private')
        if self.value() == 'group':
            return queryset.filter(type='group')
        return queryset