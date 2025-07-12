"""
Management команда для блокировки неактивных пользователей

Эта команда может запускаться как вручную администратором,
так и автоматически через cron или другие планировщики.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Блокирует пользователей, которые не заходили более указанного времени'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Количество дней неактивности (по умолчанию 30)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать пользователей для блокировки без реального блокирования',
        )
        parser.add_argument(
            '--exclude-superusers',
            action='store_true',
            help='Исключить суперпользователей из блокировки',
        )
        parser.add_argument(
            '--send-notifications',
            action='store_true',
            help='Отправить уведомления заблокированным пользователям',
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        exclude_superusers = options['exclude_superusers']
        send_notifications = options['send_notifications']

        self.stdout.write(
            f'🔍 Поиск пользователей неактивных более {days} дней...\n'
        )

        # Вычисляем дату границы неактивности
        cutoff_date = timezone.now() - timedelta(days=days)

        # Базовый queryset для поиска неактивных пользователей
        inactive_users = User.objects.filter(
            is_active=True,  # Ищем только активных пользователей
            last_login__lt=cutoff_date,  # Которые не заходили давно
            last_login__isnull=False  # И у которых есть история входа
        )

        # Исключаем суперпользователей если указано
        if exclude_superusers:
            inactive_users = inactive_users.filter(is_superuser=False)
            self.stdout.write('   ℹ️  Суперпользователи исключены из проверки')

        # Получаем список пользователей и их информацию
        users_data = []
        for user in inactive_users:
            days_inactive = (timezone.now() - user.last_login).days
            users_data.append({
                'user': user,
                'days_inactive': days_inactive,
                'last_login': user.last_login
            })

        # Сортируем по количеству дней неактивности (сначала самые неактивные)
        users_data.sort(key=lambda x: x['days_inactive'], reverse=True)

        # Выводим статистику
        total_users = User.objects.filter(is_active=True).count()
        inactive_count = len(users_data)

        self.stdout.write('📊 Статистика пользователей:')
        self.stdout.write(f'   👥 Всего активных пользователей: {total_users}')
        self.stdout.write(f'   😴 Неактивных более {days} дней: {inactive_count}')
        self.stdout.write(f'   📈 Процент неактивных: {(inactive_count / total_users * 100):.1f}%\n')

        if not users_data:
            self.stdout.write(
                self.style.SUCCESS('✅ Неактивных пользователей не найдено!')
            )
            return

        # Показываем список пользователей для блокировки
        self.stdout.write('📋 Пользователи для блокировки:')
        self.stdout.write('=' * 80)

        for data in users_data:
            user = data['user']
            days_inactive = data['days_inactive']
            last_login = data['last_login']

            # Определяем статус пользователя
            status_info = []
            if user.is_superuser:
                status_info.append('ADMIN')
            if user.is_staff:
                status_info.append('STAFF')

            status_text = f"[{', '.join(status_info)}]" if status_info else ""

            self.stdout.write(
                f'📧 {user.email:30} | '
                f'😴 {days_inactive:3d} дней | '
                f'🕐 {last_login.strftime("%Y-%m-%d")} {status_text}'
            )

        self.stdout.write('=' * 80)

        # Если это dry run - не блокируем
        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'\n🔍 DRY RUN: Найдено {inactive_count} пользователей для блокировки'
                )
            )
            self.stdout.write('   Запустите без --dry-run для реального блокирования\n')
            return

        # Подтверждение блокировки
        if inactive_count > 10:
            self.stdout.write(
                self.style.WARNING(
                    f'\n⚠️  ВНИМАНИЕ: Будет заблокировано {inactive_count} пользователей!'
                )
            )
            confirm = input('Продолжить блокировку? (введите "да" для подтверждения): ')

            if confirm.lower() not in ['да', 'yes', 'y']:
                self.stdout.write('❌ Блокировка отменена пользователем')
                return

        # Выполняем блокировку
        self.stdout.write(f'\n🔒 Блокировка {inactive_count} пользователей...')

        blocked_users = []
        for data in users_data:
            user = data['user']
            try:
                user.is_active = False
                user.save(update_fields=['is_active'])
                blocked_users.append(user)

                logger.info(
                    f'Пользователь {user.email} заблокирован '
                    f'(неактивен {data["days_inactive"]} дней)'
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Ошибка блокировки {user.email}: {e}')
                )

        # Результаты блокировки
        blocked_count = len(blocked_users)
        self.stdout.write(
            self.style.SUCCESS(f'✅ Успешно заблокировано: {blocked_count} пользователей')
        )

        if blocked_count != inactive_count:
            failed_count = inactive_count - blocked_count
            self.stdout.write(
                self.style.ERROR(f'❌ Ошибки блокировки: {failed_count} пользователей')
            )

        # Отправка уведомлений заблокированным пользователям
        if send_notifications and blocked_users:
            self.stdout.write('\n📧 Отправка уведомлений заблокированным пользователям...')

            try:
                from users.tasks import send_account_blocked_notification

                for user in blocked_users:
                    send_account_blocked_notification.delay(
                        user_id=user.id,
                        days_inactive=data['days_inactive']
                    )

                self.stdout.write(
                    self.style.SUCCESS(
                        f'✅ Запущена отправка уведомлений для {blocked_count} пользователей'
                    )
                )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'❌ Ошибка отправки уведомлений: {e}')
                )

        # Логирование для мониторинга
        if blocked_count > 0:
            # Можно отправить уведомление администраторам
            try:
                from users.tasks import send_admin_notification_about_blocked_users

                blocked_emails = [user.email for user in blocked_users]
                send_admin_notification_about_blocked_users.delay(
                    blocked_count=blocked_count,
                    blocked_emails=blocked_emails
                )

            except Exception as e:
                logger.error(f'Ошибка отправки уведомления админам: {e}')

        self.stdout.write('\n📊 Итоговая статистика:')
        self.stdout.write(f'   🔍 Проверено пользователей: {total_users}')
        self.stdout.write(f'   😴 Найдено неактивных: {inactive_count}')
        self.stdout.write(f'   🔒 Заблокировано: {blocked_count}')
        self.stdout.write(f'   ⏰ Граница неактивности: {cutoff_date.strftime("%Y-%m-%d %H:%M")}')

        if send_notifications:
            self.stdout.write(f'   📧 Уведомления отправлены: {blocked_count}')

    def get_user_activity_stats(self):
        """Возвращает статистику активности пользователей"""
        now = timezone.now()

        # Различные периоды активности
        periods = {
            'day': now - timedelta(days=1),
            'week': now - timedelta(days=7),
            'month': now - timedelta(days=30),
            'quarter': now - timedelta(days=90),
        }

        stats = {}
        for period_name, cutoff in periods.items():
            active_count = User.objects.filter(
                is_active=True,
                last_login__gte=cutoff
            ).count()
            stats[period_name] = active_count

        return stats