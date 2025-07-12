from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

from .models import User

logger = logging.getLogger(__name__)


@shared_task(bind=True, ignore_result=True)
def send_course_update_notification(self, user_email, course_title, course_id):
    """
    Асинхронная отправка уведомления об обновлении курса

    Args:
        user_email (str): Email пользователя
        course_title (str): Название курса
        course_id (int): ID курса
    """
    try:
        subject = f'Обновление курса: {course_title}'
        message = f'''
        Здравствуйте!

        Курс "{course_title}", на который вы подписаны, был обновлен.

        Переходите на платформу, чтобы ознакомиться с новыми материалами!

        С уважением,
        Команда OnlineEdu
        '''

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )

        logger.info(f'Уведомление отправлено {user_email} об обновлении курса {course_title}')
        return f'Уведомление отправлено {user_email}'

    except Exception as e:
        logger.error(f'Ошибка отправки уведомления {user_email}: {str(e)}')
        # Повторная попытка через 60 секунд, максимум 3 попытки
        raise self.retry(exc=e, countdown=60, max_retries=3)


@shared_task(bind=True, ignore_result=True)
def send_bulk_course_notifications(self, course_id, course_title, subscriber_emails):
    """
    Массовая отправка уведомлений подписчикам курса

    Args:
        course_id (int): ID курса
        course_title (str): Название курса
        subscriber_emails (list): Список email'ов подписчиков
    """
    success_count = 0
    error_count = 0

    for email in subscriber_emails:
        try:
            # Запускаем отдельную задачу для каждого пользователя
            send_course_update_notification.delay(email, course_title, course_id)
            success_count += 1
        except Exception as e:
            logger.error(f'Ошибка запуска задачи для {email}: {str(e)}')
            error_count += 1

    logger.info(
        f'Запущено {success_count} задач уведомлений для курса {course_title}. '
        f'Ошибок: {error_count}'
    )

    return {
        'course_id': course_id,
        'course_title': course_title,
        'success_count': success_count,
        'error_count': error_count
    }


@shared_task(bind=True, ignore_result=True)
def deactivate_inactive_users(self):
    """
    Периодическая задача для деактивации пользователей,
    которые не заходили более месяца
    """
    try:
        # Дата месяц назад
        one_month_ago = timezone.now() - timedelta(days=30)

        # Находим активных пользователей, которые не заходили месяц
        inactive_users = User.objects.filter(
            is_active=True,
            last_login__lt=one_month_ago
        ).exclude(
            last_login__isnull=True  # Исключаем пользователей которые никогда не заходили
        )

        # Подсчитываем количество найденных пользователей
        users_count = inactive_users.count()

        if users_count == 0:
            logger.info('Неактивных пользователей для деактивации не найдено')
            return 'Неактивных пользователей не найдено'

        # Деактивируем пользователей
        updated_count = inactive_users.update(is_active=False)

        # Логируем результат
        logger.info(f'Деактивировано {updated_count} пользователей')

        # Отправляем уведомления деактивированным пользователям (опционально)
        for user in inactive_users[:updated_count]:
            send_deactivation_notification.delay(user.email, user.first_name)

        return f'Деактивировано {updated_count} пользователей'

    except Exception as e:
        logger.error(f'Ошибка при деактивации пользователей: {str(e)}')
        raise self.retry(exc=e, countdown=300, max_retries=3)  # Повтор через 5 минут


@shared_task(bind=True, ignore_result=True)
def send_deactivation_notification(self, user_email, user_name):
    """
    Отправка уведомления о деактивации аккаунта

    Args:
        user_email (str): Email пользователя
        user_name (str): Имя пользователя
    """
    try:
        subject = 'Аккаунт был деактивирован'
        message = f'''
        Здравствуйте, {user_name or 'Уважаемый пользователь'}!

        Ваш аккаунт в системе OnlineEdu был деактивирован из-за отсутствия активности 
        более месяца.

        Если вы хотите продолжить использование платформы, обратитесь в службу поддержки 
        для восстановления доступа.

        С уважением,
        Команда OnlineEdu
        '''

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )

        logger.info(f'Уведомление о деактивации отправлено {user_email}')
        return f'Уведомление о деактивации отправлено {user_email}'

    except Exception as e:
        logger.error(f'Ошибка отправки уведомления о деактивации {user_email}: {str(e)}')
        # Не повторяем отправку уведомлений о деактивации
        return f'Ошибка отправки: {str(e)}'


@shared_task(bind=True, ignore_result=True)
def send_test_email(self, recipient_email):
    """
    Тестовая задача для проверки работы email и Celery

    Args:
        recipient_email (str): Email получателя
    """
    try:
        send_mail(
            subject='Тестовое письмо от OnlineEdu',
            message='Это тестовое письмо для проверки работы Celery и email.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            fail_silently=False,
        )

        logger.info(f'Тестовое письмо отправлено {recipient_email}')
        return f'Тестовое письмо отправлено {recipient_email}'

    except Exception as e:
        logger.error(f'Ошибка отправки тестового письма {recipient_email}: {str(e)}')
        raise self.retry(exc=e, countdown=30, max_retries=2)