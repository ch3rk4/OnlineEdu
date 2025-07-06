from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from django.utils.html import format_html
from django.urls import reverse
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
    list_display = ('email', 'first_name', 'last_name', 'phone', 'city', 'is_staff', 'get_groups', 'payments_info')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'city', 'groups')
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions')

    def get_groups(self, obj):
        """Показывает группы пользователя"""
        return ", ".join([group.name for group in obj.groups.all()]) or "Нет групп"

    get_groups.short_description = 'Группы'

    def payments_info(self, obj):
        """Показывает краткую информацию о платежах пользователя"""
        total_payments = obj.payments.count()
        stripe_payments = obj.payments.filter(payment_method='stripe').count()
        completed_payments = obj.payments.filter(status='completed').count()

        return format_html(
            'Всего: {} | Stripe: {} | Завершено: {}',
            total_payments, stripe_payments, completed_payments
        )

    payments_info.short_description = 'Платежи'


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'get_item', 'amount', 'payment_method',
        'status', 'payment_date', 'stripe_link'
    )
    list_filter = (
        'payment_method', 'status', 'payment_date', 'course', 'lesson'
    )
    search_fields = (
        'user__email', 'course__title', 'lesson__title',
        'stripe_session_id', 'description'
    )
    date_hierarchy = 'payment_date'
    ordering = ('-payment_date',)
    autocomplete_fields = ['user', 'course', 'lesson']
    readonly_fields = (
        'payment_date', 'updated_at', 'stripe_product_id',
        'stripe_price_id', 'stripe_session_id', 'stripe_checkout_url',
        'stripe_dashboard_link'
    )

    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'course', 'lesson', 'amount', 'description')
        }),
        ('Статус и метод оплаты', {
            'fields': ('payment_method', 'status', 'payment_date', 'updated_at')
        }),
        ('Stripe интеграция', {
            'fields': (
                'stripe_product_id', 'stripe_price_id', 'stripe_session_id',
                'stripe_checkout_url', 'stripe_dashboard_link'
            ),
            'classes': ('collapse',)
        }),
    )

    def get_item(self, obj):
        """Показывает что именно было оплачено"""
        if obj.course:
            return format_html(
                '<a href="{}">{}: {}</a>',
                reverse('admin:lms_course_change', args=[obj.course.pk]),
                "Курс",
                obj.course.title
            )
        elif obj.lesson:
            return format_html(
                '<a href="{}">{}: {}</a>',
                reverse('admin:lms_lesson_change', args=[obj.lesson.pk]),
                "Урок",
                obj.lesson.title
            )
        return "Не указано"

    get_item.short_description = 'Оплаченный элемент'
    get_item.admin_order_field = 'course__title'

    def stripe_link(self, obj):
        """Ссылка на платеж в Stripe"""
        if obj.stripe_session_id:
            return format_html(
                '<a href="{}" target="_blank">Stripe ↗</a>',
                obj.stripe_checkout_url or '#'
            )
        return '-'

    stripe_link.short_description = 'Stripe'

    def stripe_dashboard_link(self, obj):
        """Ссылка на дашборд Stripe"""
        if obj.stripe_session_id:
            stripe_dashboard_url = f"https://dashboard.stripe.com/test/payments/{obj.stripe_session_id}"
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                stripe_dashboard_url,
                stripe_dashboard_url
            )
        return "Нет Stripe сессии"

    stripe_dashboard_link.short_description = 'Ссылка на Stripe Dashboard'

    def get_queryset(self, request):
        """Оптимизация запросов"""
        return super().get_queryset(request).select_related('user', 'course', 'lesson')

    def save_model(self, request, obj, form, change):
        """Автоматически устанавливаем пользователя при создании через админку"""
        if not change and not obj.user_id:
            obj.user = request.user
        super().save_model(request, obj, form, change)

    # Действия для массового изменения статуса
    def mark_as_completed(self, request, queryset):
        """Отмечает выбранные платежи как завершенные"""
        updated = queryset.update(status='completed')
        self.message_user(
            request,
            f'{updated} платежей отмечено как завершенные.'
        )

    mark_as_completed.short_description = "Отметить как завершенные"

    def mark_as_failed(self, request, queryset):
        """Отмечает выбранные платежи как неудачные"""
        updated = queryset.update(status='failed')
        self.message_user(
            request,
            f'{updated} платежей отмечено как неудачные.'
        )

    mark_as_failed.short_description = "Отметить как неудачные"

    actions = [mark_as_completed, mark_as_failed]