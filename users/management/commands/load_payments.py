import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from users.models import User, Payment
from lms.models import Course, Lesson


class Command(BaseCommand):
    help = 'Загружает тестовые данные для платежей'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=20,
            help='Количество платежей для создания'
        )

    def handle(self, *args, **options):
        count = options['count']

        # Проверяем наличие пользователей
        if not User.objects.exists():
            self.stdout.write(
                self.style.ERROR('Сначала создайте пользователей')
            )
            return

        # Проверяем наличие курсов и уроков
        if not Course.objects.exists() and not Lesson.objects.exists():
            self.stdout.write(
                self.style.ERROR('Сначала создайте курсы и уроки')
            )
            return

        users = list(User.objects.all())
        courses = list(Course.objects.all())
        lessons = list(Lesson.objects.all())

        payment_methods = ['cash', 'transfer']

        payments_created = 0

        for i in range(count):
            user = random.choice(users)
            payment_method = random.choice(payment_methods)
            amount = Decimal(random.randint(1000, 50000))

            # Случайно выбираем что оплачивать - курс или урок
            if courses and lessons:
                if random.choice([True, False]):
                    # Оплачиваем курс
                    course = random.choice(courses)
                    lesson = None
                else:
                    # Оплачиваем урок
                    course = None
                    lesson = random.choice(lessons)
            elif courses:
                course = random.choice(courses)
                lesson = None
            elif lessons:
                course = None
                lesson = random.choice(lessons)
            else:
                continue

            payment = Payment.objects.create(
                user=user,
                course=course,
                lesson=lesson,
                amount=amount,
                payment_method=payment_method
            )

            payments_created += 1

            if payments_created % 5 == 0:
                self.stdout.write(f'Создано {payments_created} платежей...')

        self.stdout.write(
            self.style.SUCCESS(
                f'Успешно создано {payments_created} платежей'
            )
        )