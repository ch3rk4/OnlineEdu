"""
Management команда для проверки статуса Celery

Эта команда помогает администраторам быстро проверить:
- Работает ли Celery worker
- Доступен ли Redis брокер
- Сколько задач в очереди
- Статистика выполненных задач
"""

from django.core.management.base import BaseCommand
from django.conf import settings
from celery import Celery
import redis
import json
from datetime import datetime, timedelta


class Command(BaseCommand):
    help = 'Проверяет статус Celery workers и очередей задач'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Показать детальную информацию о задачах',
        )
        parser.add_argument(
            '--clear-failed',
            action='store_true',
            help='Очистить неудачные задачи',
        )

    def handle(self, *args, **options):
        self.stdout.write('🔍 Проверка статуса Celery системы...\n')

        # Проверка подключения к Redis
        self.check_redis_connection()

        # Проверка Celery worker'ов
        self.check_celery_workers()

        # Статистика задач
        self.show_task_statistics(detailed=options['detailed'])

        # Проверка расписания celery-beat
        self.check_beat_schedule()

        # Очистка неудачных задач если запрошено
        if options['clear_failed']:
            self.clear_failed_tasks()

    def check_redis_connection(self):
        """Проверяет подключение к Redis"""
        try:
            # Парсим Redis URL из настроек
            redis_url = settings.CELERY_BROKER_URL

            # Создаем подключение к Redis
            r = redis.from_url(redis_url)

            # Проверяем подключение
            r.ping()

            # Получаем информацию о Redis
            info = r.info()

            self.stdout.write(
                self.style.SUCCESS('✅ Redis подключение: OK')
            )
            self.stdout.write(f'   📍 Версия Redis: {info.get("redis_version", "неизвестно")}')
            self.stdout.write(f'   💾 Используемая память: {info.get("used_memory_human", "неизвестно")}')
            self.stdout.write(f'   🔗 Подключений: {info.get("connected_clients", "неизвестно")}\n')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Redis подключение: ОШИБКА - {e}\n')
            )

    def check_celery_workers(self):
        """Проверяет активные Celery worker'ы"""
        try:
            from config.celery import app as celery_app

            # Получаем информацию об активных worker'ах
            inspect = celery_app.control.inspect()

            # Проверяем активные worker'ы
            active_workers = inspect.active()

            if active_workers:
                self.stdout.write(
                    self.style.SUCCESS('✅ Celery Workers: АКТИВНЫ')
                )

                for worker_name, tasks in active_workers.items():
                    self.stdout.write(f'   🔧 Worker: {worker_name}')
                    self.stdout.write(f'      📊 Активных задач: {len(tasks)}')

                    if tasks:
                        for task in tasks[:3]:  # Показываем только первые 3 задачи
                            task_name = task.get('name', 'неизвестно')
                            task_id = task.get('id', 'неизвестно')[:8]
                            self.stdout.write(f'         🔄 {task_name} ({task_id}...)')

                # Проверяем зарегистрированные задачи
                registered = inspect.registered()
                if registered:
                    total_tasks = sum(len(tasks) for tasks in registered.values())
                    self.stdout.write(f'   📋 Зарегистрированных задач: {total_tasks}')

                self.stdout.write('')

            else:
                self.stdout.write(
                    self.style.WARNING('⚠️  Celery Workers: НЕ НАЙДЕНЫ')
                )
                self.stdout.write('   Запустите worker командой: celery -A config worker -l info\n')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка проверки workers: {e}\n')
            )

    def show_task_statistics(self, detailed=False):
        """Показывает статистику выполнения задач"""
        try:
            from django_celery_results.models import TaskResult
            from django.utils import timezone

            # Общая статистика
            total_tasks = TaskResult.objects.count()

            # Статистика за последние 24 часа
            day_ago = timezone.now() - timedelta(hours=24)
            recent_tasks = TaskResult.objects.filter(date_created__gte=day_ago)

            # Статистика по статусам
            status_stats = {}
            for status in ['SUCCESS', 'FAILURE', 'PENDING', 'RETRY']:
                count = recent_tasks.filter(status=status).count()
                status_stats[status] = count

            self.stdout.write('📊 Статистика задач:')
            self.stdout.write(f'   📈 Всего задач в БД: {total_tasks}')
            self.stdout.write(f'   🕐 За последние 24 часа: {recent_tasks.count()}')
            self.stdout.write('')

            # Детализация по статусам
            for status, count in status_stats.items():
                if status == 'SUCCESS':
                    style = self.style.SUCCESS
                    emoji = '✅'
                elif status == 'FAILURE':
                    style = self.style.ERROR
                    emoji = '❌'
                elif status == 'PENDING':
                    style = self.style.WARNING
                    emoji = '⏳'
                else:
                    style = self.style.WARNING
                    emoji = '🔄'

                self.stdout.write(style(f'   {emoji} {status}: {count}'))

            # Детальная информация если запрошена
            if detailed:
                self.stdout.write('\n📋 Последние задачи:')

                latest_tasks = TaskResult.objects.order_by('-date_created')[:10]

                for task in latest_tasks:
                    status_emoji = {
                        'SUCCESS': '✅',
                        'FAILURE': '❌',
                        'PENDING': '⏳',
                        'RETRY': '🔄'
                    }.get(task.status, '❓')

                    self.stdout.write(
                        f'   {status_emoji} {task.task_name} '
                        f'({task.date_created.strftime("%H:%M:%S")})'
                    )

                    if task.status == 'FAILURE' and task.traceback:
                        # Показываем краткую информацию об ошибке
                        error_lines = task.traceback.split('\n')
                        error_msg = next((line for line in reversed(error_lines) if line.strip()), 'Неизвестная ошибка')
                        self.stdout.write(f'      💥 {error_msg[:100]}...')

            self.stdout.write('')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка получения статистики: {e}\n')
            )

    def check_beat_schedule(self):
        """Проверяет расписание celery-beat"""
        try:
            from django.conf import settings

            self.stdout.write('⏰ Расписание Celery Beat:')

            if hasattr(settings, 'CELERY_BEAT_SCHEDULE'):
                schedule = settings.CELERY_BEAT_SCHEDULE

                if schedule:
                    for task_name, config in schedule.items():
                        task_function = config.get('task', 'неизвестно')
                        schedule_info = config.get('schedule', 'неизвестно')

                        # Преобразуем schedule в читаемый формат
                        if isinstance(schedule_info, (int, float)):
                            schedule_text = f'каждые {schedule_info} секунд'
                        else:
                            schedule_text = str(schedule_info)

                        self.stdout.write(f'   📅 {task_name}:')
                        self.stdout.write(f'      🎯 Задача: {task_function}')
                        self.stdout.write(f'      ⏱️  Расписание: {schedule_text}')
                else:
                    self.stdout.write('   📝 Периодических задач не настроено')
            else:
                self.stdout.write('   ⚠️  CELERY_BEAT_SCHEDULE не найден в настройках')

            self.stdout.write('')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка проверки расписания: {e}\n')
            )

    def clear_failed_tasks(self):
        """Очищает неудачные задачи из базы данных"""
        try:
            from django_celery_results.models import TaskResult

            failed_tasks = TaskResult.objects.filter(status='FAILURE')
            count = failed_tasks.count()

            if count > 0:
                failed_tasks.delete()
                self.stdout.write(
                    self.style.SUCCESS(f'🧹 Очищено {count} неудачных задач')
                )
            else:
                self.stdout.write('✨ Неудачных задач для очистки не найдено')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибка очистки задач: {e}')
            )

    def handle_no_color(self, *args, **options):
        """Версия без цветов для логов"""
        return self.handle(*args, **options)