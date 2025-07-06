from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from unittest.mock import patch, MagicMock
from decimal import Decimal

from .models import User, Payment
from .services import StripeService
from lms.models import Course, Lesson


class StripeServiceTestCase(TestCase):
    """Тесты для StripeService"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        self.course = Course.objects.create(
            title='Test Course',
            description='Test Description',
            owner=self.user
        )

    @patch('stripe.Product.create')
    def test_create_product_success(self, mock_create):
        """Тест успешного создания продукта в Stripe"""
        # Мокаем ответ Stripe
        mock_product = MagicMock()
        mock_product.id = 'prod_test123'
        mock_product.name = 'Test Course'
        mock_product.description = 'Test Description'
        mock_create.return_value = mock_product

        result = StripeService.create_product(
            name='Test Course',
            description='Test Description'
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['product_id'], 'prod_test123')
        self.assertEqual(result['name'], 'Test Course')

    @patch('stripe.Product.create')
    def test_create_product_failure(self, mock_create):
        """Тест ошибки при создании продукта в Stripe"""
        import stripe
        mock_create.side_effect = stripe.error.StripeError("Test error")

        result = StripeService.create_product(
            name='Test Course',
            description='Test Description'
        )

        self.assertFalse(result['success'])
        self.assertIn('error', result)

    @patch('stripe.Price.create')
    def test_create_price_success(self, mock_create):
        """Тест успешного создания цены в Stripe"""
        mock_price = MagicMock()
        mock_price.id = 'price_test123'
        mock_price.unit_amount = 150000  # 1500.00 рублей в копейках
        mock_price.currency = 'rub'
        mock_create.return_value = mock_price

        result = StripeService.create_price(
            product_id='prod_test123',
            amount=150000,
            currency='rub'
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['price_id'], 'price_test123')
        self.assertEqual(result['amount'], 150000)

    @patch('stripe.checkout.Session.create')
    def test_create_checkout_session_success(self, mock_create):
        """Тест успешного создания сессии оплаты"""
        mock_session = MagicMock()
        mock_session.id = 'cs_test123'
        mock_session.url = 'https://checkout.stripe.com/pay/cs_test123'
        mock_session.payment_status = 'unpaid'
        mock_create.return_value = mock_session

        result = StripeService.create_checkout_session(
            price_id='price_test123',
            success_url='http://localhost:3000/success',
            cancel_url='http://localhost:3000/cancel',
            customer_email='test@example.com'
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['session_id'], 'cs_test123')
        self.assertEqual(result['checkout_url'], 'https://checkout.stripe.com/pay/cs_test123')

    @patch('users.services.StripeService.create_product')
    @patch('users.services.StripeService.create_price')
    @patch('users.services.StripeService.create_checkout_session')
    def test_create_course_payment_success(self, mock_session, mock_price, mock_product):
        """Тест создания полного цикла оплаты курса"""
        # Мокаем успешные ответы
        mock_product.return_value = {
            'success': True,
            'product_id': 'prod_test123'
        }

        mock_price.return_value = {
            'success': True,
            'price_id': 'price_test123'
        }

        mock_session.return_value = {
            'success': True,
            'session_id': 'cs_test123',
            'checkout_url': 'https://checkout.stripe.com/pay/cs_test123'
        }

        result = StripeService.create_course_payment(
            course=self.course,
            user=self.user,
            amount=1500.0
        )

        self.assertTrue(result['success'])
        self.assertEqual(result['product_id'], 'prod_test123')
        self.assertEqual(result['price_id'], 'price_test123')
        self.assertEqual(result['session_id'], 'cs_test123')


class StripePaymentAPITestCase(APITestCase):
    """Тесты для API создания Stripe платежей"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        self.course = Course.objects.create(
            title='Test Course',
            description='Test Description',
            owner=self.user
        )

        self.lesson = Lesson.objects.create(
            title='Test Lesson',
            description='Test Lesson Description',
            video_url='https://youtube.com/watch?v=test123',
            course=self.course,
            owner=self.user
        )

        self.create_payment_url = reverse('stripe-payment-create')

    @patch('users.services.StripeService.create_course_payment')
    def test_create_stripe_payment_for_course(self, mock_create_payment):
        """Тест создания Stripe платежа для курса"""
        self.client.force_authenticate(user=self.user)

        # Мокаем успешный ответ от Stripe
        mock_create_payment.return_value = {
            'success': True,
            'product_id': 'prod_test123',
            'price_id': 'price_test123',
            'session_id': 'cs_test123',
            'checkout_url': 'https://checkout.stripe.com/pay/cs_test123',
            'amount': 1500.0,
            'currency': 'rub'
        }

        data = {
            'course_id': self.course.id,
            'amount': '1500.00'
        }

        response = self.client.post(self.create_payment_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn('checkout_url', response.data['payment'])

        # Проверяем что платеж создан в базе
        payment = Payment.objects.get(user=self.user, course=self.course)
        self.assertEqual(payment.amount, Decimal('1500.00'))
        self.assertEqual(payment.payment_method, 'stripe')
        self.assertEqual(payment.status, 'pending')

    @patch('users.services.StripeService.create_lesson_payment')
    def test_create_stripe_payment_for_lesson(self, mock_create_payment):
        """Тест создания Stripe платежа для урока"""
        self.client.force_authenticate(user=self.user)

        mock_create_payment.return_value = {
            'success': True,
            'product_id': 'prod_test123',
            'price_id': 'price_test123',
            'session_id': 'cs_test123',
            'checkout_url': 'https://checkout.stripe.com/pay/cs_test123',
            'amount': 500.0,
            'currency': 'rub'
        }

        data = {
            'lesson_id': self.lesson.id,
            'amount': '500.00'
        }

        response = self.client.post(self.create_payment_url, data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])

        # Проверяем что платеж создан в базе
        payment = Payment.objects.get(user=self.user, lesson=self.lesson)
        self.assertEqual(payment.amount, Decimal('500.00'))

    def test_create_payment_validation_errors(self):
        """Тест валидации при создании платежа"""
        self.client.force_authenticate(user=self.user)

        # Без суммы
        response = self.client.post(self.create_payment_url, {
            'course_id': self.course.id
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Без course_id и lesson_id
        response = self.client.post(self.create_payment_url, {
            'amount': '1500.00'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # И course_id и lesson_id одновременно
        response = self.client.post(self.create_payment_url, {
            'course_id': self.course.id,
            'lesson_id': self.lesson.id,
            'amount': '1500.00'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Отрицательная сумма
        response = self.client.post(self.create_payment_url, {
            'course_id': self.course.id,
            'amount': '-100.00'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch('users.services.StripeService.create_course_payment')
    def test_create_payment_stripe_error(self, mock_create_payment):
        """Тест обработки ошибки Stripe"""
        self.client.force_authenticate(user=self.user)

        # Мокаем ошибку от Stripe
        mock_create_payment.return_value = {
            'success': False,
            'error': 'Stripe API error'
        }

        data = {
            'course_id': self.course.id,
            'amount': '1500.00'
        }

        response = self.client.post(self.create_payment_url, data)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

        # Проверяем что платеж НЕ создан в базе
        self.assertFalse(Payment.objects.filter(user=self.user, course=self.course).exists())

    def test_create_payment_unauthenticated(self):
        """Тест создания платежа без аутентификации"""
        data = {
            'course_id': self.course.id,
            'amount': '1500.00'
        }

        response = self.client.post(self.create_payment_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PaymentStatusAPITestCase(APITestCase):
    """Тесты для API проверки статуса платежа"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        self.course = Course.objects.create(
            title='Test Course',
            description='Test Description',
            owner=self.user
        )

        self.payment = Payment.objects.create(
            user=self.user,
            course=self.course,
            amount=Decimal('1500.00'),
            payment_method='stripe',
            status='pending',
            stripe_session_id='cs_test123'
        )

    @patch('users.services.StripeService.retrieve_session')
    def test_check_payment_status_success(self, mock_retrieve):
        """Тест успешной проверки статуса платежа"""
        self.client.force_authenticate(user=self.user)

        # Мокаем ответ от Stripe
        mock_retrieve.return_value = {
            'success': True,
            'session_id': 'cs_test123',
            'payment_status': 'paid',
            'amount_total': 150000,
            'currency': 'rub',
            'customer_email': 'test@example.com',
            'created': 1234567890,
            'expires_at': 1234571490
        }

        url = reverse('stripe-payment-status', kwargs={'payment_id': self.payment.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('stripe_data', response.data)

        # Проверяем что статус платежа обновился
        self.payment.refresh_from_db()
        self.assertEqual(self.payment.status, 'completed')

    def test_check_payment_status_not_owner(self):
        """Тест проверки статуса чужого платежа"""
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=other_user)

        url = reverse('stripe-payment-status', kwargs={'payment_id': self.payment.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_check_payment_status_non_stripe(self):
        """Тест проверки статуса не-Stripe платежа"""
        self.client.force_authenticate(user=self.user)

        # Создаем не-Stripe платеж
        cash_payment = Payment.objects.create(
            user=self.user,
            course=self.course,
            amount=Decimal('1000.00'),
            payment_method='cash',
            status='completed'
        )

        url = reverse('stripe-payment-status', kwargs={'payment_id': cash_payment.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserStripePaymentsAPITestCase(APITestCase):
    """Тесты для API получения Stripe платежей пользователя"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        self.course = Course.objects.create(
            title='Test Course',
            description='Test Description',
            owner=self.user
        )

        # Создаем разные типы платежей
        Payment.objects.create(
            user=self.user,
            course=self.course,
            amount=Decimal('1500.00'),
            payment_method='stripe',
            status='completed'
        )

        Payment.objects.create(
            user=self.user,
            course=self.course,
            amount=Decimal('1000.00'),
            payment_method='cash',
            status='completed'
        )

        Payment.objects.create(
            user=self.user,
            course=self.course,
            amount=Decimal('2000.00'),
            payment_method='stripe',
            status='pending'
        )

    def test_get_user_stripe_payments(self):
        """Тест получения Stripe платежей пользователя"""
        self.client.force_authenticate(user=self.user)

        url = reverse('user-stripe-payments')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)  # Только Stripe платежи

        # Проверяем что все платежи имеют payment_method='stripe'
        for payment in response.data['payments']:
            self.assertEqual(payment['payment_method'], 'stripe')

    def test_get_stripe_payments_unauthenticated(self):
        """Тест получения платежей без аутентификации"""
        url = reverse('user-stripe-payments')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class PaymentModelTestCase(TestCase):
    """Тесты для модели Payment"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123'
        )

        self.course = Course.objects.create(
            title='Test Course',
            description='Test Description',
            owner=self.user
        )

    def test_payment_properties(self):
        """Тест свойств модели Payment"""
        payment = Payment.objects.create(
            user=self.user,
            course=self.course,
            amount=Decimal('1500.00'),
            payment_method='stripe',
            stripe_session_id='cs_test123'
        )

        # Тест item_title
        self.assertEqual(payment.item_title, 'Test Course')

        # Тест is_stripe_payment
        self.assertTrue(payment.is_stripe_payment)

        # Тест для не-Stripe платежа
        cash_payment = Payment.objects.create(
            user=self.user,
            course=self.course,
            amount=Decimal('1000.00'),
            payment_method='cash'
        )

        self.assertFalse(cash_payment.is_stripe_payment)

    def test_update_from_stripe_session(self):
        """Тест обновления статуса из Stripe сессии"""
        payment = Payment.objects.create(
            user=self.user,
            course=self.course,
            amount=Decimal('1500.00'),
            payment_method='stripe',
            status='pending'
        )

        # Тест успешного платежа
        stripe_data = {
            'success': True,
            'payment_status': 'paid'
        }

        payment.update_from_stripe_session(stripe_data)
        self.assertEqual(payment.status, 'completed')

        # Тест неоплаченного платежа
        stripe_data = {
            'success': True,
            'payment_status': 'unpaid'
        }

        payment.update_from_stripe_session(stripe_data)
        self.assertEqual(payment.status, 'pending')