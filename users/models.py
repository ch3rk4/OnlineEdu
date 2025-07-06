from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Кастомный менеджер для модели пользователя без поля username"""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email обязателен')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Суперпользователь должен иметь is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Суперпользователь должен иметь is_superuser=True.')

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True, verbose_name='Email')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='Телефон')
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name='Город')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='Аватар')

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('cash', 'Наличные'),
        ('transfer', 'Перевод на счет'),
        ('stripe', 'Stripe (банковская карта)'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Ожидает оплаты'),
        ('processing', 'Обрабатывается'),
        ('completed', 'Завершен'),
        ('failed', 'Ошибка'),
        ('cancelled', 'Отменен'),
        ('refunded', 'Возвращен'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='Пользователь'
    )
    payment_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    course = models.ForeignKey(
        'lms.Course',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name='Оплаченный курс'
    )
    lesson = models.ForeignKey(
        'lms.Lesson',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='payments',
        verbose_name='Оплаченный урок'
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Сумма оплаты'
    )
    payment_method = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name='Способ оплаты'
    )
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending',
        verbose_name='Статус платежа'
    )

    # Поля для интеграции со Stripe
    stripe_product_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='ID продукта в Stripe'
    )
    stripe_price_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='ID цены в Stripe'
    )
    stripe_session_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='ID сессии в Stripe'
    )
    stripe_checkout_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='Ссылка на оплату Stripe'
    )

    # Дополнительные поля
    description = models.TextField(
        blank=True,
        verbose_name='Описание платежа'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Платеж'
        verbose_name_plural = 'Платежи'
        ordering = ['-payment_date']

    def __str__(self):
        item = self.course or self.lesson
        return f'{self.user.email} - {item} - {self.amount} руб. ({self.get_status_display()})'

    def clean(self):
        from django.core.exceptions import ValidationError
        if not self.course and not self.lesson:
            raise ValidationError('Должен быть указан либо курс, либо урок')
        if self.course and self.lesson:
            raise ValidationError('Нельзя указывать одновременно курс и урок')

    @property
    def item_title(self):
        """Возвращает название оплачиваемого элемента"""
        if self.course:
            return self.course.title
        elif self.lesson:
            return self.lesson.title
        return "Неизвестно"

    @property
    def is_stripe_payment(self):
        """Проверяет является ли платеж через Stripe"""
        return self.payment_method == 'stripe' and bool(self.stripe_session_id)

    def update_from_stripe_session(self, session_data):
        """Обновляет платеж данными из Stripe сессии"""
        if session_data.get('success'):
            payment_status = session_data.get('payment_status', 'pending')

            # Маппинг статусов Stripe на наши статусы
            status_mapping = {
                'paid': 'completed',
                'unpaid': 'pending',
                'no_payment_required': 'completed'
            }

            self.status = status_mapping.get(payment_status, 'pending')
            self.save(update_fields=['status', 'updated_at'])