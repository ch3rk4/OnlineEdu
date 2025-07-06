import random
from django.core.management.base import BaseCommand
from users.models import User
from lms.models import Course, Subscription


class Command(BaseCommand):
    help = 'Создает тестовые подписки пользователей на курсы'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Количество подписок для создания'
        )

    def handle(self, *args, **options):
        count = options['count']

        # Получаем пользователей и курсы
        users = list(User.objects.all())
        courses = list(Course.objects.all())

        if not users:
            self.stdout.write(
                self.style.ERROR('Нет пользователей в базе данных')
            )
            return

        if not courses:
            self.stdout.write(
                self.style.ERROR('Нет курсов в базе данных')
            )
            return

        created_count = 0
        attempts = 0
        max_attempts = count * 3  # Предотвращаем бесконечный цикл

        while created_count < count and attempts < max_attempts:
            attempts += 1

            user = random.choice(users)
            course = random.choice(courses)

            # Проверяем что подписка еще не существует
            if not Subscription.objects.filter(user=user, course=course).exists():
                # Не подписываем владельца на свой же курс (опционально)
                if user != course.owner:
                    Subscription.objects.create(
                        user=user,
                        course=course,
                        is_active=random.choice([True, True, True, False])  # 75% активных
                    )
                    created_count += 1

                    if created_count % 5 == 0:
                        self.stdout.write(f'Создано {created_count} подписок...')

        self.stdout.write(
            self.style.SUCCESS(
                f'Успешно создано {created_count} подписок'
            )
        )

        # Статистика
        total_subscriptions = Subscription.objects.count()
        active_subscriptions = Subscription.objects.filter(is_active=True).count()

        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(f'Всего подписок в базе: {total_subscriptions}')
        self.stdout.write(f'Активных подписок: {active_subscriptions}')
        self.stdout.write(f'Неактивных подписок: {total_subscriptions - active_subscriptions}')
        self.stdout.write('=' * 50)