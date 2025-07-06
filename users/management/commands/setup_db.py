from django.core.management.base import BaseCommand
from django.core.management import call_command
import os


class Command(BaseCommand):
    help = 'Настройка базы данных: миграции, группы, тестовые данные'

    def add_arguments(self, parser):
        parser.add_argument(
            '--with-data',
            action='store_true',
            help='Загрузить тестовые данные после миграций'
        )
        parser.add_argument(
            '--skip-migrate',
            action='store_true',
            help='Пропустить выполнение миграций'
        )

    def handle(self, *args, **options):
        self.stdout.write('🚀 Настройка базы данных OnlineEdu...')

        if not options['skip_migrate']:
            # Применяем миграции
            self.stdout.write('\n📦 Применение миграций...')
            try:
                call_command('migrate', verbosity=0)
                self.stdout.write(
                    self.style.SUCCESS('✅ Миграции применены успешно')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Ошибка при применении миграций: {e}')
                )
                return

        # Создаем группы
        self.stdout.write('\n👥 Создание групп пользователей...')
        try:
            call_command('create_groups', verbosity=0)
            self.stdout.write(
                self.style.SUCCESS('✅ Группы созданы успешно')
            )
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Предупреждение при создании групп: {e}')
            )

        if options['with_data']:
            # Загружаем тестовые данные
            self.stdout.write('\n📝 Загрузка тестовых данных...')
            try:
                call_command('init_data', verbosity=0)
                self.stdout.write(
                    self.style.SUCCESS('✅ Тестовые данные загружены')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Предупреждение при загрузке данных: {e}')
                )

            # Загружаем тестовые платежи
            self.stdout.write('\n💳 Загрузка тестовых платежей...')
            try:
                call_command('load_payments', '--count', '20', verbosity=0)
                self.stdout.write(
                    self.style.SUCCESS('✅ Тестовые платежи загружены')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f'⚠️  Предупреждение при загрузке платежей: {e}')
                )

        # Выводим статистику
        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('📊 СТАТИСТИКА БАЗЫ ДАННЫХ')
        self.stdout.write('=' * 60)

        from users.models import User, Payment
        from lms.models import Course, Lesson, Subscription
        from django.contrib.auth.models import Group

        self.stdout.write(f'👥 Пользователей: {User.objects.count()}')
        self.stdout.write(f'🎓 Курсов: {Course.objects.count()}')
        self.stdout.write(f'📚 Уроков: {Lesson.objects.count()}')
        self.stdout.write(f'💳 Платежей: {Payment.objects.count()}')
        self.stdout.write(f'📧 Подписок: {Subscription.objects.count()}')
        self.stdout.write(f'🔰 Групп: {Group.objects.count()}')

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(
            self.style.SUCCESS('✅ База данных настроена успешно!')
        )

        self.stdout.write('\n📋 Следующие шаги:')
        self.stdout.write('1. Создайте суперпользователя: python manage.py createsuperuser')
        self.stdout.write('2. Запустите сервер: python manage.py runserver')
        self.stdout.write('3. Откройте API документацию: http://localhost:8000/api/docs/')
        self.stdout.write('4. Админка: http://localhost:8000/admin/')

        if options['with_data']:
            self.stdout.write('5. Добавьте пользователей в группу "Moderators" через админку')

        self.stdout.write('=' * 60)