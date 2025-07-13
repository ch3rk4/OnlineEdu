"""
Асинхронные задачи для приложения users

Celery позволяет выполнять тяжелые операции в фоне, не блокируя
основное веб-приложение. Это особенно важно для:
- Отправки email (может занимать несколько секунд)
- Обработки больших объемов данных
- Операций с внешними API
"""

import time
import logging
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from datetime import timedelta

User = get_user_model()
logger = logging.getLogger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def send_course_update_notification(self, user_id, course_title, course_id, update_type='general'):
    """
    Отправляет уведомление пользователю об обновлении курса

    Параметры:
    - user_id: ID пользователя, которому отправляем уведомление
    - course_title: Название курса
    - course_id: ID курса
    - update_type: Тип обновления ('general', 'new_lesson', 'lesson_updated')

    @shared_task означает, что это Celery задача
    bind=True позволяет получать доступ к контексту задачи (self)
    autoretry_for автоматически повторяет задачу при ошибках
    """
    try:
        # Получаем пользователя из базы данных
        user = User.objects.get(id=user_id)

        # Определяем тему письма в зависимости от типа обновления
        subject_map = {
            'general': f'Обновление курса: {course_title}',
            'new_lesson': f'Новый урок в курсе: {course_title}',
            'lesson_updated': f'Урок обновлен в курсе: {course_title}'
        }

        subject = subject_map.get(update_type, f'Обновление курса: {course_title}')

        # Контекст для шаблона письма
        email_context = {
            'user': user,
            'course_title': course_title,
            'course_id': course_id,
            'update_type': update_type,
            'course_url': f"{settings.FRONTEND_URL}/courses/{course_id}",
            'unsubscribe_url': f"{settings.FRONTEND_URL}/unsubscribe/{course_id}",
        }

        # Рендерим HTML и текстовую версию письма
        try:
            html_message = render_to_string('emails/course_update.html', email_context)
            text_message = render_to_string('emails/course_update.txt', email_context)
        except Exception as template_error:
            # Если шаблоны не найдены, используем простое сообщение
            logger.warning(f"Шаблоны email не найдены, используем простое сообщение: {template_error}")
            html_message = f"""
            <h2>Обновление курса: {course_title}</h2>
            <p>Привет, {user.first_name or user.email}!</p>
            <p>В курсе "{course_title}" появились обновления.</p>
            <p><a href="{settings.FRONTEND_URL}/courses/{course_id}">Перейти к курсу</a></p>
            """
            text_message = f"""
            Обновление курса: {course_title}
            
            Привет, {user.first_name or user.email}!
            
            В курсе "{course_title}" появились обновления.
            
            Перейти к курсу: {settings.FRONTEND_URL}/courses/{course_id}
            """

        # Отправляем письмо
        send_mail(
            subject=subject,
            message=text_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,  # Поднимаем исключение при ошибке
        )

        logger.info(f"Уведомление отправлено пользователю {user.email} о курсе {course_title}")
        return f"Email успешно отправлен пользователю {user.email}"

    except User.DoesNotExist:
        logger.error(f"Пользователь с ID {user_id} не найден")
        raise Exception(f"Пользователь с ID {user_id} не существует")

    except Exception as e:
        logger.error(f"Ошибка при отправке email пользователю {user_id}: {str(e)}")
        # Celery автоматически повторит задачу благодаря autoretry_for
        raise


@shared_task(bind=True)
def send_bulk_course_notifications(self, course_id, course_title, update_type='general'):
    """
    Отправляет уведомления всем подписчикам курса

    Эта задача запускает множество подзадач для каждого подписчика.
    Такой подход позволяет:
    1. Обрабатывать ошибки для каждого пользователя отдельно
    2. Повторять неудачные отправки независимо
    3. Отслеживать прогресс для каждого пользователя
    """
    try:
        from lms.models import Subscription

        # Получаем всех активных подписчиков курса
        subscriptions = Subscription.objects.filter(
            course_id=course_id,
            is_active=True
        ).select_related('user')

        # Считаем количество подписчиков
        subscriber_count = subscriptions.count()

        if subscriber_count == 0:
            logger.info(f"У курса {course_title} нет активных подписчиков")
            return "Нет подписчиков для уведомления"

        # Запускаем отдельную задачу для каждого подписчика
        sent_count = 0
        for subscription in subscriptions:
            try:
                # .delay() запускает задачу асинхронно
                send_course_update_notification.delay(
                    user_id=subscription.user.id,
                    course_title=course_title,
                    course_id=course_id,
                    update_type=update_type
                )
                sent_count += 1

            except Exception as e:
                logger.error(f"Ошибка при запуске задачи для пользователя {subscription.user.id}: {e}")

        logger.info(f"Запущено {sent_count} задач уведомления для курса {course_title}")
        return f"Уведомления отправлены {sent_count} подписчикам курса {course_title}"

    except Exception as e:
        logger.error(f"Ошибка при массовой отправке уведомлений для курса {course_id}: {e}")
        raise


@shared_task(bind=True)
def block_inactive_users(self):
    """
    Периодическая задача для блокировки неактивных пользователей

    Эта задача запускается по расписанию через celery-beat и:
    1. Находит пользователей, которые не заходили более месяца
    2. Блокирует их, устанавливая is_active=False
    3. Логирует результаты для мониторинга
    """
    try:
        # Вычисляем дату месяц назад от текущего момента
        one_month_ago = timezone.now() - timedelta(days=30)

        # Находим пользователей, которые:
        # 1. Активны (is_active=True)
        # 2. Не заходили более месяца (last_login меньше месяца назад)
        # 3. Имеют запись о входе (last_login не равен None)
        # 4. Не являются суперпользователями (для безопасности)
        inactive_users = User.objects.filter(
            is_active=True,
            last_login__lt=one_month_ago,
            last_login__isnull=False,
            is_superuser=False  # Не блокируем суперпользователей
        )

        # Считаем количество пользователей для блокировки
        users_to_block = inactive_users.count()

        if users_to_block == 0:
            logger.info("Неактивных пользователей для блокировки не найдено")
            return "Неактивных пользователей не найдено"

        # Получаем список email заблокированных пользователей для логирования
        blocked_emails = list(inactive_users.values_list('email', flat=True))

        # Блокируем пользователей (массовое обновление - эффективнее чем по одному)
        blocked_count = inactive_users.update(is_active=False)

        logger.info(f"Заблокировано {blocked_count} неактивных пользователей: {blocked_emails}")

        # Опционально: можно отправить уведомления админам
        if blocked_count > 0:
            send_admin_notification_about_blocked_users.delay(
                blocked_count=blocked_count,
                blocked_emails=blocked_emails
            )

        return f"Заблокировано {blocked_count} неактивных пользователей"

    except Exception as e:
        logger.error(f"Ошибка при блокировке неактивных пользователей: {e}")
        raise


@shared_task(bind=True)
def send_admin_notification_about_blocked_users(self, blocked_count, blocked_emails):
    """
    Отправляет уведомление админам о заблокированных пользователях

    Эта задача помогает администраторам отслеживать автоматическую
    блокировку пользователей.
    """
    try:
        # Получаем список админов
        admin_users = User.objects.filter(is_superuser=True, is_active=True)

        if not admin_users.exists():
            logger.warning("Не найдено активных администраторов для уведомления")
            return "Нет админов для уведомления"

        # Формируем содержимое письма
        subject = f"Заблокировано {blocked_count} неактивных пользователей"
        message = f"""
        Система автоматически заблокировала {blocked_count} пользователей, 
        которые не заходили более месяца.

        Заблокированные пользователи:
        {chr(10).join(blocked_emails)}

        Время блокировки: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}
        """

        # Отправляем уведомление каждому админу
        for admin in admin_users:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin.email],
                fail_silently=True,  # Не прерываем выполнение при ошибке
            )

        logger.info(f"Уведомления о блокировке отправлены {admin_users.count()} администраторам")
        return f"Уведомления отправлены {admin_users.count()} админам"

    except Exception as e:
        logger.error(f"Ошибка при отправке уведомлений админам: {e}")
        # Не поднимаем исключение, чтобы не прерывать основную задачу
        return f"Ошибка отправки уведомлений: {e}"


@shared_task(bind=True)
def cleanup_old_celery_results(self):
    """
    Очистка старых результатов Celery задач

    Эта задача помогает поддерживать чистоту в Redis/БД,
    удаляя устаревшие результаты выполнения задач.
    """
    try:
        from django_celery_results.models import TaskResult

        # Удаляем результаты старше 7 дней
        week_ago = timezone.now() - timedelta(days=7)

        deleted_count, _ = TaskResult.objects.filter(
            date_created__lt=week_ago
        ).delete()

        logger.info(f"Удалено {deleted_count} старых результатов Celery задач")
        return f"Очищено {deleted_count} записей"

    except Exception as e:
        logger.error(f"Ошибка при очистке результатов Celery: {e}")
        raise


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def send_account_blocked_notification(self, user_id, days_inactive):
    """
    Отправляет уведомление пользователю о блокировке аккаунта

    Параметры:
    - user_id: ID заблокированного пользователя
    - days_inactive: Количество дней неактивности
    """
    try:
        user = User.objects.get(id=user_id)

        # Тема письма
        subject = f'Ваш аккаунт OnlineEdu временно заблокирован'

        # Контекст для email шаблона
        email_context = {
            'user': user,
            'days_inactive': days_inactive,
            'reactivation_url': f"{settings.FRONTEND_URL}/reactivate",
            'support_email': 'support@onlineedu.com',
            'login_url': f"{settings.FRONTEND_URL}/login",
        }

        # Рендерим шаблоны
        try:
            html_message = render_to_string('emails/account_blocked.html', email_context)
            text_message = render_to_string('emails/account_blocked.txt', email_context)
        except Exception:
            # Fallback если шаблоны не найдены
            html_message = f"""
            <h2>Ваш аккаунт временно заблокирован</h2>
            <p>Привет, {user.first_name or user.email}!</p>
            <p>Ваш аккаунт был заблокирован из-за неактивности ({days_inactive} дней).</p>
            <p>Для восстановления доступа свяжитесь с поддержкой: support@onlineedu.com</p>
            """
            text_message = f"""
            Ваш аккаунт OnlineEdu временно заблокирован
            
            Привет, {user.first_name or user.email}!
            
            Ваш аккаунт был заблокирован из-за неактивности ({days_inactive} дней).
            
            Для восстановления доступа свяжитесь с поддержкой: support@onlineedu.com
            """

        # Отправляем уведомление
        send_mail(
            subject=subject,
            message=text_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        logger.info(f"Уведомление о блокировке отправлено пользователю {user.email}")
        return f"Уведомление о блокировке отправлено пользователю {user.email}"

    except User.DoesNotExist:
        logger.error(f"Пользователь с ID {user_id} не найден для уведомления о блокировке")
        raise Exception(f"Пользователь с ID {user_id} не существует")

    except Exception as e:
        logger.error(f"Ошибка отправки уведомления о блокировке пользователю {user_id}: {str(e)}")
        raise


@shared_task(bind=True)
def send_welcome_email(self, user_id):
    """
    Отправляет приветственное письмо новому пользователю

    Эта задача может быть вызвана после регистрации пользователя
    """
    try:
        user = User.objects.get(id=user_id)

        subject = f'Добро пожаловать в OnlineEdu, {user.first_name or user.email}!'

        email_context = {
            'user': user,
            'courses_url': f"{settings.FRONTEND_URL}/courses",
            'profile_url': f"{settings.FRONTEND_URL}/profile",
            'support_email': 'support@onlineedu.com',
        }

        try:
            html_message = render_to_string('emails/welcome.html', email_context)
            text_message = render_to_string('emails/welcome.txt', email_context)
        except Exception:
            # Fallback если шаблоны не найдены
            html_message = f"""
            <h2>Добро пожаловать в OnlineEdu!</h2>
            <p>Привет, {user.first_name or user.email}!</p>
            <p>Спасибо за регистрацию на нашей образовательной платформе.</p>
            <p><a href="{settings.FRONTEND_URL}/courses">Перейти к курсам</a></p>
            """
            text_message = f"""
            Добро пожаловать в OnlineEdu!
            
            Привет, {user.first_name or user.email}!
            
            Спасибо за регистрацию на нашей образовательной платформе.
            
            Перейти к курсам: {settings.FRONTEND_URL}/courses
            """

        send_mail(
            subject=subject,
            message=text_message,
            html_message=html_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        logger.info(f"Приветственное письмо отправлено пользователю {user.email}")
        return f"Приветственное письмо отправлено пользователю {user.email}"

    except Exception as e:
        logger.error(f"Ошибка отправки приветственного письма пользователю {user_id}: {e}")
        raise


@shared_task(bind=True)
def send_promotional_email(self, user_ids, subject, template_name, context_data=None):
    """
    Отправляет промо-письма группе пользователей

    Параметры:
    - user_ids: список ID пользователей
    - subject: тема письма
    - template_name: имя шаблона (без расширения)
    - context_data: дополнительные данные для шаблона
    """
    try:
        context_data = context_data or {}
        sent_count = 0
        failed_count = 0

        for user_id in user_ids:
            try:
                user = User.objects.get(id=user_id, is_active=True)

                # Базовый контекст для всех промо-писем
                email_context = {
                    'user': user,
                    'unsubscribe_url': f"{settings.FRONTEND_URL}/unsubscribe",
                    'courses_url': f"{settings.FRONTEND_URL}/courses",
                    **context_data  # Добавляем дополнительные данные
                }

                try:
                    html_message = render_to_string(f'emails/{template_name}.html', email_context)
                    text_message = render_to_string(f'emails/{template_name}.txt', email_context)
                except Exception:
                    # Fallback если шаблоны не найдены
                    html_message = f"""
                    <h2>{subject}</h2>
                    <p>Привет, {user.first_name or user.email}!</p>
                    <p>У нас есть интересные новости для вас!</p>
                    <p><a href="{settings.FRONTEND_URL}/courses">Перейти к курсам</a></p>
                    """
                    text_message = f"""
                    {subject}
                    
                    Привет, {user.first_name or user.email}!
                    
                    У нас есть интересные новости для вас!
                    
                    Перейти к курсам: {settings.FRONTEND_URL}/courses
                    """

                send_mail(
                    subject=subject,
                    message=text_message,
                    html_message=html_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )

                sent_count += 1

                # Небольшая задержка между отправками для предотвращения блокировки SMTP
                time.sleep(0.1)

            except User.DoesNotExist:
                logger.warning(f"Пользователь {user_id} не найден для промо-рассылки")
                failed_count += 1
            except Exception as e:
                logger.error(f"Ошибка отправки промо-письма пользователю {user_id}: {e}")
                failed_count += 1

        logger.info(f"Промо-рассылка завершена: отправлено {sent_count}, ошибок {failed_count}")
        return f"Отправлено {sent_count} писем, ошибок: {failed_count}"

    except Exception as e:
        logger.error(f"Ошибка промо-рассылки: {e}")
        raise


@shared_task(bind=True)
def generate_user_activity_report(self):
    """
    Генерирует отчет об активности пользователей

    Эта задача может запускаться еженедельно для анализа вовлеченности
    """
    try:
        from django.db.models import Count
        from lms.models import Course, Subscription
        from users.models import Payment

        now = timezone.now()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        # Собираем статистику
        stats = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'weekly_active': User.objects.filter(
                last_login__gte=week_ago,
                is_active=True
            ).count(),
            'monthly_active': User.objects.filter(
                last_login__gte=month_ago,
                is_active=True
            ).count(),
            'new_registrations_week': User.objects.filter(
                date_joined__gte=week_ago
            ).count(),
        }

        # Статистика по курсам
        stats.update({
            'total_courses': Course.objects.count(),
            'total_subscriptions': Subscription.objects.filter(is_active=True).count(),
            'new_subscriptions_week': Subscription.objects.filter(
                created_at__gte=week_ago,
                is_active=True
            ).count(),
        })

        # Отправляем отчет администраторам
        admin_users = User.objects.filter(is_superuser=True, is_active=True)

        for admin in admin_users:
            # Простое текстовое сообщение если шаблонов нет
            subject = f'Еженедельный отчет активности OnlineEdu - {now.strftime("%Y-%m-%d")}'
            message = f"""
            Еженедельный отчет активности OnlineEdu
            
            Дата отчета: {now.strftime('%Y-%m-%d %H:%M')}
            
            ПОЛЬЗОВАТЕЛИ:
            - Всего пользователей: {stats['total_users']}
            - Активных пользователей: {stats['active_users']}
            - Активных за неделю: {stats['weekly_active']}
            - Активных за месяц: {stats['monthly_active']}
            - Новых регистраций за неделю: {stats['new_registrations_week']}
            
            КУРСЫ:
            - Всего курсов: {stats['total_courses']}
            - Всего подписок: {stats['total_subscriptions']}
            - Новых подписок за неделю: {stats['new_subscriptions_week']}
            """

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[admin.email],
                fail_silently=True,
            )

        logger.info(f"Отчет об активности сгенерирован и отправлен {admin_users.count()} администраторам")
        return f"Отчет отправлен {admin_users.count()} администраторам: {stats}"

    except Exception as e:
        logger.error(f"Ошибка генерации отчета активности: {e}")
        raise