from django.db import models
from django.conf import settings


class Course(models.Model):
    title = models.CharField(max_length=200, verbose_name='Название')
    preview = models.ImageField(upload_to='courses/', blank=True, null=True, verbose_name='Превью')
    description = models.TextField(verbose_name='Описание')
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='courses',
        verbose_name='Владелец'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'

    def __str__(self):
        return self.title

    last_notification_sent = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Время последнего уведомления',
        help_text='Когда в последний раз отправлялись уведомления подписчикам об обновлении курса'
    )

    # Поле для включения/отключения уведомлений
    notification_enabled = models.BooleanField(
        default=True,
        verbose_name='Уведомления включены',
        help_text='Разрешать ли отправку уведомлений при обновлении курса'
    )

    def can_send_notification(self):
        """
        Проверяет, можно ли отправить уведомление о курсе

        Возвращает True, если:
        1. Уведомления включены для курса
        2. Прошло более 4 часов с последнего уведомления
        3. Есть активные подписчики
        """
        from django.utils import timezone
        from datetime import timedelta

        # Проверяем, включены ли уведомления
        if not self.notification_enabled:
            return False, "Уведомления отключены для этого курса"

        # Проверяем временной интервал
        if self.last_notification_sent:
            four_hours_ago = timezone.now() - timedelta(hours=4)
            if self.last_notification_sent > four_hours_ago:
                return False, "Слишком рано для следующего уведомления"

        # Проверяем наличие подписчиков
        active_subscribers = self.subscriptions.filter(is_active=True).count()
        if active_subscribers == 0:
            return False, "Нет активных подписчиков"

        return True, f"Можно отправить уведомление {active_subscribers} подписчикам"

    def get_notification_stats(self):
        """
        Возвращает статистику уведомлений для курса
        """
        from django.utils import timezone
        from datetime import timedelta

        stats = {
            'notifications_enabled': self.notification_enabled,
            'last_notification_sent': self.last_notification_sent,
            'active_subscribers': self.subscriptions.filter(is_active=True).count(),
            'total_subscribers': self.subscriptions.count(),
        }

        if self.last_notification_sent:
            stats['hours_since_last_notification'] = (
                                                             timezone.now() - self.last_notification_sent
                                                     ).total_seconds() / 3600

            four_hours_ago = timezone.now() - timedelta(hours=4)
            stats['can_send_notification'] = self.last_notification_sent <= four_hours_ago
        else:
            stats['hours_since_last_notification'] = None
            stats['can_send_notification'] = True

        return stats


class Lesson(models.Model):
    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    preview = models.ImageField(upload_to='lessons/', blank=True, null=True, verbose_name='Превью')
    video_url = models.URLField(verbose_name='Ссылка на видео')
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name='Курс'
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name='Владелец'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Урок'
        verbose_name_plural = 'Уроки'

    def __str__(self):
        return f'{self.course.title} - {self.title}'


class Subscription(models.Model):
    """Модель подписки пользователя на обновления курса"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Пользователь'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Курс'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата подписки')
    is_active = models.BooleanField(default=True, verbose_name='Активна')

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        unique_together = ('user', 'course')  # Один пользователь не может подписаться на курс дважды
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} подписан на {self.course.title}'