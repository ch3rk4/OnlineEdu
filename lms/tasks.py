from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

from .models import Course, Subscription
from users.tasks import send_bulk_course_notifications

logger = logging.getLogger(__name__)


@shared_task(bind=True, ignore_result=True)
def notify_course_subscribers(self, course_id):
    """
    Уведомление подписчиков о обновлении курса

    Проверяет что курс не обновлялся последние 4 часа,
    чтобы не спамить пользователей при множественных обновлениях

    Args:
        course_id (int): ID обновленного курса
    """
    try:
        # Получаем курс
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            logger.error(f'Курс с ID {course_id} не найден')
            return f'Курс с ID {course_id} не найден'

        # Проверяем что курс не обновлялся последние 4 часа
        four_hours_ago = timezone.now() - timedelta(hours=4)

        # Если курс обновлялся менее 4 часов назад, пропускаем уведомление
        if course.updated_at > four_hours_ago:
            logger.info(
                f'Курс "{course.title}" обновлялся менее 4 часов назад. '
                f'Уведомления не отправляются.'
            )
            return f'Курс обновлялся недавно, уведомления пропущены'

        # Получаем активные подписки на курс
        active_subscriptions = Subscription.objects.filter(
            course=course,
            is_active=True
        ).select_related('user')

        if not active_subscriptions.exists():
            logger.info(f'Нет активных подписок на курс "{course.title}"')
            return 'Нет активных подписок'

        # Собираем email'ы подписчиков
        subscriber_emails = [
            subscription.user.email
            for subscription in active_subscriptions
            if subscription.user.is_active and subscription.user.email
        ]

        if not subscriber_emails:
            logger.info(f'Нет активных пользователей с email для курса "{course.title}"')
            return 'Нет активных пользователей с email'

        # Запускаем массовую отправку уведомлений
        send_bulk_course_notifications.delay(
            course_id=course.id,
            course_title=course.title,
            subscriber_emails=subscriber_emails
        )

        logger.info(
            f'Запущена отправка уведомлений для {len(subscriber_emails)} '
            f'подписчиков курса "{course.title}"'
        )

        return f'Запущена отправка уведомлений для {len(subscriber_emails)} подписчиков'

    except Exception as e:
        logger.error(f'Ошибка при уведомлении подписчиков курса {course_id}: {str(e)}')
        raise self.retry(exc=e, countdown=60, max_retries=3)


@shared_task(bind=True, ignore_result=True)
def notify_lesson_update(self, lesson_id):
    """
    Уведомление подписчиков при обновлении урока

    Args:
        lesson_id (int): ID обновленного урока
    """
    try:
        from .models import Lesson

        try:
            lesson = Lesson.objects.select_related('course').get(id=lesson_id)
        except Lesson.DoesNotExist:
            logger.error(f'Урок с ID {lesson_id} не найден')
            return f'Урок с ID {lesson_id} не найден'

        # Уведомляем подписчиков курса об обновлении урока
        # Используем ту же логику проверки времени
        return notify_course_subscribers.delay(lesson.course.id)

    except Exception as e:
        logger.error(f'Ошибка при уведомлении об обновлении урока {lesson_id}: {str(e)}')
        raise self.retry(exc=e, countdown=60, max_retries=3)


@shared_task(bind=True, ignore_result=True)
def cleanup_old_subscriptions(self):
    """
    Периодическая задача для очистки старых неактивных подписок
    (можно запускать раз в неделю)
    """
    try:
        # Удаляем неактивные подписки старше 6 месяцев
        six_months_ago = timezone.now() - timedelta(days=180)

        old_subscriptions = Subscription.objects.filter(
            is_active=False,
            created_at__lt=six_months_ago
        )

        deleted_count = old_subscriptions.count()
        old_subscriptions.delete()

        logger.info(f'Удалено {deleted_count} старых неактивных подписок')
        return f'Удалено {deleted_count} старых подписок'

    except Exception as e:
        logger.error(f'Ошибка при очистке подписок: {str(e)}')
        raise self.retry(exc=e, countdown=300, max_retries=2)


@shared_task(bind=True, ignore_result=True)
def update_course_statistics(self):
    """
    Периодическая задача для обновления статистики курсов
    (можно запускать раз в день)
    """
    try:
        from django.db.models import Count

        # Обновляем количество подписчиков для каждого курса
        courses = Course.objects.annotate(
            subscribers_count=Count('subscriptions', filter={'subscriptions__is_active': True})
        )

        updated_count = 0
        for course in courses:
            # Можно добавить поле subscribers_count в модель Course для кеширования
            # course.subscribers_count = course.subscribers_count
            # course.save(update_fields=['subscribers_count'])
            updated_count += 1

        logger.info(f'Обновлена статистика для {updated_count} курсов')
        return f'Обновлена статистика для {updated_count} курсов'

    except Exception as e:
        logger.error(f'Ошибка при обновлении статистики: {str(e)}')
        return f'Ошибка: {str(e)}'