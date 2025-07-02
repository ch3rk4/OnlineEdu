from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Payment


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
    list_display = ('email', 'first_name', 'last_name', 'phone', 'city', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'city')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_item', 'amount', 'payment_method', 'payment_date')
    list_filter = ('payment_method', 'payment_date', 'course', 'lesson')
    search_fields = ('user__email', 'course__title', 'lesson__title')
    date_hierarchy = 'payment_date'
    ordering = ('-payment_date',)

    def get_item(self, obj):
        """Показывает что именно было оплачено"""
        if obj.course:
            return f"Курс: {obj.course.title}"
        elif obj.lesson:
            return f"Урок: {obj.lesson.title}"
        return "Не указано"
    get_item.short_description = 'Оплаченный элемент'