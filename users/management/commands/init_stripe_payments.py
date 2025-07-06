import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from users.models import User, Payment
from lms.models import Course, Lesson


class Command(BaseCommand):
    help = 'Создает тестовые Stripe платежи для демонстрации'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='Количество Stripe платежей для создания'
        )
        parser.add_argument(
            '--with-stripe-data',
            action='store_true',
            help='Создать платежи с мок-данными Stripe (для тестирования UI)'
        )

    def handle(self, *args, **options):
        count = options['count']
        with_stripe_data = options['with_stripe_data']

        # Проверяем наличие пользователей
        if not User.objects.exists():
            self.stdout.write(
                self.style.ERROR('Сначала создайте пользователей с помощью: python manage.py init_data')
            )
            return

        # Проверяем наличие курсов и уроков
        if not Course.objects.exists() and not Lesson.objects.exists():
            self.stdout.write(
                self.style.ERROR('Сначала создайте курсы и уроки с помощью: python manage.py init_data')
            )
            return

        users = list(User.objects.all())
        courses = list(Course.objects.all())
        lessons = list(Lesson.objects.all())

        # Возможные статусы для Stripe платежей
        stripe_statuses = ['pending', 'completed', 'failed', 'cancelled']

        # Реальные суммы для курсов/уроков
        course_amounts = [Decimal('5000.00'), Decimal('10000.00'), Decimal('15000.00'), Decimal('20000.00')]
        lesson_amounts = [Decimal('500.00'), Decimal('1000.00'), Decimal('1500.00'), Decimal('2500.00')]

        payments_created = 0

        self.stdout.write(f'Создание {count} тестовых Stripe платежей...')

        for i in range(count):
            user = random.choice(users)
            status = random.choice(stripe_statuses)

            # Случайно выбираем что оплачивать - курс или урок
            if courses and lessons:
                if random.choice([True, False]):
                    # Оплачиваем курс
                    course = random.choice(courses)
                    lesson = None
                    amount = random.choice(course_amounts)
                    description = f"Оплата курса: {course.title}"
                else:
                    # Оплачиваем урок
                    course = None
                    lesson = random.choice(lessons)
                    amount = random.choice(lesson_amounts)
                    description = f"Оплата урока: {lesson.title} (курс: {lesson.course.title})"
            elif courses:
                course = random.choice(courses)
                lesson = None
                amount = random.choice(course_amounts)
                description = f"Оплата курса: {course.title}"
            elif lessons:
                course = None
                lesson = random.choice(lessons)
                amount = random.choice(lesson_amounts)
                description = f"Оплата урока: {lesson.title}"
            else:
                continue

            # Создаем базовый платеж
            payment_data = {
                'user': user,
                'course': course,
                'lesson': lesson,
                'amount': amount,
                'payment_method': 'stripe',
                'status': status,
                'description': description
            }

            # Добавляем мок-данные Stripe если запрошено
            if with_stripe_data:
                payment_id = f"cs_test_{random.randint(100000, 999999)}"
                product_id = f"prod_test_{random.randint(100000, 999999)}"
                price_id = f"price_test_{random.randint(100000, 999999)}"

                payment_data.update({
                    'stripe_session_id': payment_id,
                    'stripe_product_id': product_id,
                    'stripe_price_id': price_id,
                    'stripe_checkout_url': f"https://checkout.stripe.com/c/pay/{payment_id}"
                })

            payment = Payment.objects.create(**payment_data)
            payments_created += 1

            if payments_created % 5 == 0:
                self.stdout.write(f'Создано {payments_created} платежей...')

        self.stdout.write(
            self.style.SUCCESS(
                f'Успешно создано {payments_created} Stripe платежей'
            )
        )

        # Статистика
        total_stripe_payments = Payment.objects.filter(payment_method='stripe').count()
        completed_stripe = Payment.objects.filter(payment_method='stripe', status='completed').count()
        pending_stripe = Payment.objects.filter(payment_method='stripe', status='pending').count()

        total_amount = sum(
            p.amount for p in Payment.objects.filter(payment_method='stripe', status='completed')
        )

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write('📊 СТАТИСТИКА STRIPE ПЛАТЕЖЕЙ')
        self.stdout.write('=' * 60)
        self.stdout.write(f'Всего Stripe платежей: {total_stripe_payments}')
        self.stdout.write(f'Завершенных: {completed_stripe}')
        self.stdout.write(f'Ожидающих: {pending_stripe}')
        self.stdout.write(f'Общая сумма завершенных: {total_amount:,.2f} ₽')

        if with_stripe_data:
            self.stdout.write(f'✅ Созданы с мок-данными Stripe')
        else:
            self.stdout.write(f'ℹ️  Созданы без Stripe данных (добавьте --with-stripe-data)')

        self.stdout.write('\n📋 Следующие шаги:')
        self.stdout.write('1. Настройте Stripe ключи в .env файле')
        self.stdout.write('2. Тестируйте создание реальных платежей через API')
        self.stdout.write('3. Проверьте админку: http://localhost:8000/admin/users/payment/')
        self.stdout.write('4. Изучите API документацию: http://localhost:8000/api/docs/')
        self.stdout.write('=' * 60)