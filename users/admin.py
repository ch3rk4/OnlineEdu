from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from .models import User, Payment


# Кастомизируем отображение групп в админке
class GroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'users_count')
    filter_horizontal = ('permissions',)

    def users_count(self, obj):
        return obj.user_set.count()

    users_count.short_description = 'Количество пользователей'


# Перерегистрируем Group admin
admin.site.unregister(Group)
admin.site.register(Group, GroupAdmin)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Персональная информация', {'fields': ('first_name', 'last_name', 'phone', 'city', 'avatar')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Важные даты', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    list_display = ('email', 'first_name', 'last_name', 'phone', 'city', 'is_staff', 'get_groups')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'city', 'groups')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions')

    def get_groups(self, obj):
        """Показывает группы пользователя"""
        return ", ".join([group.name for group in obj.groups.all()]) or "Нет групп"

    get_groups.short_description = 'Группы'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_item', 'amount', 'payment_method', 'payment_date')
    list_filter = ('payment_method', 'payment_date', 'course', 'lesson')
    search_fields = ('user__email', 'course__title', 'lesson__title')
    date_hierarchy = 'payment_date'
    ordering = ('-payment_date',)
    autocomplete_fields = ['user', 'course', 'lesson']

    def get_item(self, obj):
        """Показывает что именно было оплачено"""
        if obj.course:
            return f"Курс: {obj.course.title}"
        elif obj.lesson:
            return f"Урок: {obj.lesson.title}"
        return "Не указано"

    get_item.short_description = 'Оплаченный элемент'