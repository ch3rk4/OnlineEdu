"""
Management команда для тестирования системы уведомлений

Эта команда позволяет администраторам:
- Тестировать отправку email уведомлений
- Проверять работу email шаблонов
- Отладить проблемы с доставкой писем
- Тестировать Celery задачи в безопасном режиме
"""

from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from users.models import User
from lms.models import Course, Subscription
from users.tasks import send_course_update_notification, send_bulk_course_notifications
from lms.tasks import process_course_update_notification
import time


class Command(BaseCommand):
    help = 'Тестирует систему уведомлений и email рассылки'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email адрес для тестовых уведомлений',
        )
        parser.add_argument(
            '--course-id',
            type=int,
            help='ID курса для тестирования уведомлений',
        )
        parser.add_argument(
            '--template-test',
            action='store_true',
            help='Тестировать только шаблоны email (без отправки)',
        )
        parser.add_argument(
            '--async-test',
            action='store_true',
            help='Тестировать асинхронные Celery задачи',
        )
        parser.add_argument(
            '--bulk-test',
            action='store_true',
            help='Тестировать массовую рассылку (осторожно!)',
        )
        parser.add_argument(
            '--notification-type',
            type=str,
            choices=['general', 'new_lesson', 'lesson_updated'],
            default='general',
            help='Тип уведомления для тестирования',
        )

    def handle(self, *args, **options):
        self.stdout.write('🧪 Тестирование системы уведомлений...\n')

        # Проверяем базовые настройки
        self.check_email_settings()

        # Если указан только тест шаблонов
        if options['template_test']:
            self.test_email_templates(
                email=options.get('email'),
                course_id=options.get('course_id'),
                notification_type=options['notification_type']
            )
            return

        # Если указан тест асинхронных задач
        if options['async_test']:
            self.test_async_tasks(
                email=options.get('email'),
                course_id=options.get('course_id'),
                notification_type=options['notification_type']
            )
            return

        # Если указан тест массовой рассылки
        if options['bulk_test']:
            self.test_bulk_notifications(
                course_id=options.get('course_id'),
                notification_type=options['notification_type']
            )
            return

        # Базовый тест отправки email
        self.test_basic_email(options.get('email'))

    def check_email_settings(self):
        """Проверяет настройки email"""
        self.stdout.write('📧 Проверка настроек email:')

        # Проверяем основные настройки
        email_backend = getattr(settings, 'EMAIL_BACKEND', 'не настроен')
        email_host = getattr(settings, 'EMAIL_HOST', 'не настроен')
        default_from = getattr(settings, 'DEFAULT_FROM_EMAIL', 'не настроен')

        self.stdout.write(f'   📮 Backend: {email_backend}')
        self.stdout.write(f'   🏠 Host: {email_host}')
        self.stdout.write(f'   📨 From: {default_from}')

        # Проверяем режим разработки
        if 'console' in email_backend.lower():
            self.stdout.write(
                self.style.WARNING('   ⚠️  Режим консоли - письма будут выводиться в терминал')
            )
        elif 'filebased' in email_backend.lower():
            self.stdout.write(
                self.style.WARNING('   ⚠️  Режим файлов - письма будут сохраняться в файлы')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('   ✅ Настроен реальный SMTP')
            )

        self.stdout.write('')

    def test_basic_email(self, test_email=None):
        """Тестирует базовую отправку email"""
        # Получаем email для тестирования
        if not test_email:
            # Пытаемся найти первого активного пользователя
            test_user = User.objects.filter(is_active=True).first()
            if test_user:
                test_email = test_user.email
            else:
                self.stdout.write(
                    self.style.ERROR('❌ Не найден email для тестирования. Укажите --email')
                )
                return

        self.stdout.write(f'📤 Отправка тестового письма на {test_email}...')

        try:
            # Отправляем простое тестовое письмо
            send_mail(
                subject='Тест системы уведомлений OnlineEdu',
                message='Это тестовое письмо для проверки работы email системы.',
                html_message='''
                <h2>🧪 Тест системы уведомлений</h2>
                <p>Если вы получили это письмо, значит email система работает корректно!</p>
                <p><strong>Время отправки:</strong> {}</p>
                <hr>
                <p><em>OnlineEdu - Образовательная платформа</em></p>
                '''.format(time.strftime('%Y-%m-%d %H:%M:%S')),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[test_email],
                fail_silently=False,
            )

            self.stdout.write(
                self.style.SUCCESS('✅ Тестовое письмо отправлено успешно!')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка отправки: {e}')
            )

    def test_email_templates(self, email=None, course_id=None, notification_type='general'):
        """Тестирует email шаблоны без реальной отправки"""
        self.stdout.write('🎨 Тестирование email шаблонов...')

        # Получаем данные для тестирования
        test_user = self.get_test_user(email)
        test_course = self.get_test_course(course_id)

        if not test_user or not test_course:
            return

        # Создаем контекст для шаблонов
        email_context = {
            'user': test_user,
            'course_title': test_course.title,
            'course_id': test_course.id,
            'update_type': notification_type,
            'course_url': f"{settings.FRONTEND_URL}/courses/{test_course.id}",
            'unsubscribe_url': f"{settings.FRONTEND_URL}/unsubscribe/{test_course.id}",
        }

        try:
            # Тестируем HTML шаблон
            html_content = render_to_string('emails/course_update.html', email_context)
            self.stdout.write('   ✅ HTML шаблон обработан успешно')

            # Тестируем текстовый шаблон
            text_content = render_to_string('emails/course_update.txt', email_context)
            self.stdout.write('   ✅ Текстовый шаблон обработан успешно')

            # Показываем превью
            self.stdout.write('\n📋 Превью письма:')
            self.stdout.write('═' * 60)
            self.stdout.write(f'Кому: {test_user.email}')
            self.stdout.write(f'Тема: Обновление курса: {test_course.title}')
            self.stdout.write('─' * 60)

            # Показываем первые несколько строк текста
            text_lines = text_content.split('\n')[:10]
            for line in text_lines:
                self.stdout.write(line[:80])

            self.stdout.write('═' * 60)

            # Сохраняем превью в файл (опционально)
            with open('email_preview.html', 'w', encoding='utf-8') as f:
                f.write(html_content)

            self.stdout.write(
                self.style.SUCCESS('✅ Превью сохранено в email_preview.html')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка обработки шаблонов: {e}')
            )

    def test_async_tasks(self, email=None, course_id=None, notification_type='general'):
        """Тестирует асинхронные Celery задачи"""
        self.stdout.write('🔄 Тестирование асинхронных задач...')

        # Получаем данные для тестирования
        test_user = self.get_test_user(email)
        test_course = self.get_test_course(course_id)

        if not test_user or not test_course:
            return

        try:
            # Проверяем доступность Celery
            from config.celery import app as celery_app

            # Тестируем простую задачу
            self.stdout.write('   🧪 Тестирование debug задачи...')
            result = celery_app.send_task('config.celery.debug_task')

            self.stdout.write(f'   📋 Task ID: {result.id}')

            # Ждем результат (максимум 10 секунд)
            try:
                task_result = result.get(timeout=10)
                self.stdout.write(
                    self.style.SUCCESS(f'   ✅ Debug задача выполнена: {task_result}')
                )
            except Exception:
                self.stdout.write(
                    self.style.WARNING('   ⏳ Debug задача запущена асинхронно')
                )

            # Тестируем задачу уведомления
            self.stdout.write('   🧪 Тестирование задачи уведомления...')

            task = send_course_update_notification.delay(
                user_id=test_user.id,
                course_title=test_course.title,
                course_id=test_course.id,
                update_type=notification_type
            )

            self.stdout.write(f'   📋 Notification Task ID: {task.id}')
            self.stdout.write(
                self.style.SUCCESS('   ✅ Задача уведомления запущена')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка тестирования задач: {e}')
            )

    def test_bulk_notifications(self, course_id=None, notification_type='general'):
        """Тестирует массовую рассылку уведомлений"""
        self.stdout.write('📢 Тестирование массовой рассылки...')

        # Получаем курс для тестирования
        test_course = self.get_test_course(course_id)
        if not test_course:
            return

        # Проверяем количество подписчиков
        subscribers_count = test_course.subscriptions.filter(is_active=True).count()

        if subscribers_count == 0:
            self.stdout.write(
                self.style.WARNING('⚠️  У курса нет активных подписчиков')
            )
            return

        # Предупреждение о массовой рассылке
        self.stdout.write(
            self.style.WARNING(
                f'⚠️  ВНИМАНИЕ: Будет отправлено {subscribers_count} уведомлений!'
            )
        )

        confirm = input('Продолжить? (yes/no): ')
        if confirm.lower() not in ['yes', 'y', 'да']:
            self.stdout.write('❌ Отменено пользователем')
            return

        try:
            # Запускаем массовую рассылку
            task = send_bulk_course_notifications.delay(
                course_id=test_course.id,
                course_title=test_course.title,
                update_type=notification_type
            )

            self.stdout.write(f'📋 Bulk Task ID: {task.id}')
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Массовая рассылка запущена для {subscribers_count} подписчиков'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка массовой рассылки: {e}')
            )

    def get_test_user(self, email=None):
        """Получает пользователя для тестирования"""
        if email:
            try:
                return User.objects.get(email=email)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ Пользователь с email {email} не найден')
                )
                return None
        else:
            user = User.objects.filter(is_active=True).first()
            if not user:
                self.stdout.write(
                    self.style.ERROR('❌ Не найдено активных пользователей')
                )
                return None
            return user

    def get_test_course(self, course_id=None):
        """Получает курс для тестирования"""
        if course_id:
            try:
                return Course.objects.get(id=course_id)
            except Course.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'❌ Курс с ID {course_id} не найден')
                )
                return None
        else:
            course = Course.objects.first()
            if not course:
                self.stdout.write(
                    self.style.ERROR('❌ Не найдено курсов в системе')
                )
                return None
            return course