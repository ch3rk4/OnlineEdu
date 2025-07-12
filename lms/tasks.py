"""
Асинхронные задачи для приложения LMS

Эти задачи обрабатывают логику уведомлений при обновлении курсов.
Ключевая особенность - мы проверяем, не было ли курс обновлен недавно,
чтобы избежать спама уведомлений.
"""

from celery import shared_task
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_course_update_notification(self, course_id, update_type='general'):
    """
    Обрабатывает уведомления об обновлении курса с проверкой временных интервалов

    Это центральная задача, которая решает:
    1. Нужно ли отправлять уведомления (прошло ли 4 часа с последнего)
    2. Какой тип уведомления отправить
    3. Обновление времени последнего уведомления

    Параметры:
    - course_id: ID обновленного курса
    - update_type: тип обновления ('general', 'new_lesson', 'lesson_updated')
    """
    try:
        from .models import Course
        from users.tasks import send_bulk_course_notifications

        # Получаем курс из базы данных
        course = Course.objects.get(id=course_id)

        # Проверяем, прошло ли достаточно времени с последнего уведомления
        now = timezone.now()
        four_hours_ago = now - timedelta(hours=4)

        # Если у курса есть поле last_notification_sent и оно свежее 4 часов - не отправляем
        if hasattr(course, 'last_notification_sent') and course.last_notification_sent:
            if course.last_notification_sent > four_hours_ago:
                time_remaining = course.last_notification_sent + timedelta(hours=4) - now
                logger.info(
                    f"Уведомление для курса {course.title} пропущено. "
                    f"Следующее уведомление возможно через {time_remaining}"
                )
                return f"Уведомление пропущено - слишком рано (осталось {time_remaining})"

        # Проверяем есть ли подписчики у курса
        subscription_count = course.subscriptions.filter(is_active=True).count()

        if subscription_count == 0:
            logger.info(f"У курса {course.title} нет активных подписчиков")
            return "Нет подписчиков для уведомления"

        # Запускаем массовую рассылку уведомлений
        send_bulk_course_notifications.delay(
            course_id=course.id,
            course_title=course.title,
            update_type=update_type
        )

        # Обновляем время последнего уведомления
        if hasattr(course, 'last_notification_sent'):
            course.last_notification_sent = now
            course.save(update_fields=['last_notification_sent'])

        logger.info(
            f"Запущена рассылка уведомлений для {subscription_count} подписчиков курса {course.title}"
        )

        return f"Уведомления отправлены {subscription_count} подписчикам курса {course.title}"

    except Exception as e:
        logger.error(f"Ошибка при обработке уведомления для курса {course_id}: {e}")
        raise


@shared_task(bind=True)
def process_lesson_update_notification(self, lesson_id, update_type='lesson_updated'):
    """
    Обрабатывает уведомления об обновлении урока

    Урок является частью курса, поэтому мы:
    1. Получаем урок и его курс
    2. Проверяем временные ограничения на уровне курса
    3. Отправляем уведомления подписчикам курса
    """
    try:
        from .models import Lesson

        # Получаем урок и связанный курс
        lesson = Lesson.objects.select_related('course').get(id=lesson_id)
        course = lesson.course

        # Используем существующую логику для курса
        # Это обеспечивает единообразную обработку временных ограничений
        return process_course_update_notification.delay(
            course_id=course.id,
            update_type=update_type
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке уведомления для урока {lesson_id}: {e}")
        raise


@shared_task(bind=True)
def cleanup_old_data(self):
    """
    Периодическая очистка старых данных в системе

    Эта задача помогает поддерживать производительность системы,
    удаляя или архивируя устаревшие данные.
    """
    try:
        from .models import Subscription
        from users.models import Payment

        cleanup_results = {}

        # 1. Деактивируем очень старые подписки без активности
        six_months_ago = timezone.now() - timedelta(days=180)

        old_subscriptions = Subscription.objects.filter(
            created_at__lt=six_months_ago,
            is_active=True,
            # Дополнительные условия можно добавить
        )

        deactivated_subscriptions = old_subscriptions.update(is_active=False)
        cleanup_results['deactivated_subscriptions'] = deactivated_subscriptions

        # 2. Можно добавить другие операции очистки
        # Например, удаление неиспользуемых файлов медиа

        logger.info(f"Очистка данных завершена: {cleanup_results}")
        return f"Очистка завершена: {cleanup_results}"

    except Exception as e:
        logger.error(f"Ошибка при очистке данных: {e}")
        raise


@shared_task(bind=True)
def generate_course_statistics(self, course_id):
    """
    Генерирует статистику по курсу

    Эта задача может выполняться периодически или по запросу
    для создания отчетов о популярности курсов, активности студентов и т.д.
    """
    try:
        from .models import Course
        from users.models import Payment

        course = Course.objects.get(id=course_id)

        # Собираем статистику
        stats = {
            'course_id': course_id,
            'course_title': course.title,
            'generated_at': timezone.now().isoformat(),
            'total_lessons': course.lessons.count(),
            'active_subscriptions': course.subscriptions.filter(is_active=True).count(),
            'total_subscriptions': course.subscriptions.count(),
            'payments_count': Payment.objects.filter(course=course).count(),
            'completed_payments': Payment.objects.filter(
                course=course,
                status='completed'
            ).count(),
        }

        # Можно сохранить статистику в БД или отправить в аналитическую систему
        logger.info(f"Статистика для курса {course.title}: {stats}")

        return stats

    except Exception as e:
        logger.error(f"Ошибка при генерации статистики для курса {course_id}: {e}")
        raise


@shared_task(bind=True)
def send_weekly_digest(self):
    """
    Еженедельная рассылка дайджеста активности

    Отправляет пользователям сводку по их курсам:
    - Новые уроки в подписанных курсах
    - Рекомендации похожих курсов
    - Статистика обучения
    """
    try:
        from .models import Subscription
        from users.models import User
        from users.tasks import send_course_update_notification

        # Получаем пользователей с активными подписками
        active_subscribers = User.objects.filter(
            subscriptions__is_active=True,
            is_active=True
        ).distinct()

        digest_sent_count = 0

        for user in active_subscribers:
            # Для каждого пользователя собираем информацию о его курсах
            user_subscriptions = user.subscriptions.filter(is_active=True).select_related('course')

            if user_subscriptions.exists():
                # Запускаем отдельную задачу для генерации и отправки дайджеста
                send_user_weekly_digest.delay(user.id)
                digest_sent_count += 1

        logger.info(f"Запущена генерация еженедельного дайджеста для {digest_sent_count} пользователей")
        return f"Дайджест запущен для {digest_sent_count} пользователей"

    except Exception as e:
        logger.error(f"Ошибка при отправке еженедельного дайджеста: {e}")
        raise


@shared_task(bind=True)
def send_user_weekly_digest(self, user_id):
    """
    Генерирует и отправляет персональный еженедельный дайджест пользователю
    """
    try:
        from users.models import User
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings

        user = User.objects.get(id=user_id)

        # Собираем данные для дайджеста
        user_courses = user.subscriptions.filter(is_active=True).select_related('course')

        # Можно добавить логику для:
        # - Новых уроков за неделю
        # - Рекомендаций
        # - Статистики прогресса

        digest_context = {
            'user': user,
            'courses': user_courses,
            'week_start': timezone.now() - timedelta(days=7),
            'unsubscribe_url': f"{settings.FRONTEND_URL}/unsubscribe/digest",
        }

        # Рендерим и отправляем дайджест
        subject = f"Ваш еженедельный дайджест обучения"
        html_message = render_to_string('emails/weekly_digest.html', digest_context)
        text_message = render_to_string('emails/weekly_digest.txt', digest_context)

        send_mail(
            subject=subject,
            message=text_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        logger.info(f"Еженедельный дайджест отправлен пользователю {user.email}")
        return f"Дайджест отправлен пользователю {user.email}"

    except Exception as e:
        logger.error(f"Ошибка при отправке дайджеста пользователю {user_id}: {e}")
        raise