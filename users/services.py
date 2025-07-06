import stripe
from django.conf import settings
from typing import Dict, Optional
import logging

# Настройка Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

logger = logging.getLogger(__name__)


class StripeService:
    """Сервис для работы с Stripe API"""

    @staticmethod
    def create_product(name: str, description: str = None) -> Dict:
        """
        Создание продукта в Stripe

        Args:
            name: Название продукта
            description: Описание продукта

        Returns:
            Dict с данными созданного продукта
        """
        try:
            product = stripe.Product.create(
                name=name,
                description=description or f"Курс: {name}",
                type='service'  # Для услуг/курсов
            )

            logger.info(f"Создан продукт Stripe: {product.id}")
            return {
                'success': True,
                'product_id': product.id,
                'name': product.name,
                'description': product.description
            }

        except stripe.error.StripeError as e:
            logger.error(f"Ошибка создания продукта Stripe: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def create_price(product_id: str, amount: int, currency: str = 'rub') -> Dict:
        """
        Создание цены для продукта в Stripe

        Args:
            product_id: ID продукта в Stripe
            amount: Сумма в копейках (для рублей умножить на 100)
            currency: Валюта (по умолчанию RUB)

        Returns:
            Dict с данными созданной цены
        """
        try:
            price = stripe.Price.create(
                product=product_id,
                unit_amount=amount,
                currency=currency,
                billing_scheme='per_unit'
            )

            logger.info(f"Создана цена Stripe: {price.id}")
            return {
                'success': True,
                'price_id': price.id,
                'amount': price.unit_amount,
                'currency': price.currency
            }

        except stripe.error.StripeError as e:
            logger.error(f"Ошибка создания цены Stripe: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def create_checkout_session(
            price_id: str,
            success_url: str,
            cancel_url: str,
            customer_email: str = None,
            metadata: Dict = None
    ) -> Dict:
        """
        Создание сессии оплаты в Stripe

        Args:
            price_id: ID цены в Stripe
            success_url: URL для успешной оплаты
            cancel_url: URL для отмененной оплаты
            customer_email: Email покупателя
            metadata: Дополнительные данные для сессии

        Returns:
            Dict с данными сессии и ссылкой на оплату
        """
        try:
            session_data = {
                'payment_method_types': ['card'],
                'line_items': [{
                    'price': price_id,
                    'quantity': 1,
                }],
                'mode': 'payment',
                'success_url': success_url,
                'cancel_url': cancel_url,
                'expires_at': int((stripe.util.convert_to_stripe_object({
                    'current_timestamp': stripe.util.convert_to_unix_timestamp()
                }).current_timestamp + 3600))  # Истекает через час
            }

            # Добавляем email клиента если предоставлен
            if customer_email:
                session_data['customer_email'] = customer_email

            # Добавляем метаданные если предоставлены
            if metadata:
                session_data['metadata'] = metadata

            session = stripe.checkout.Session.create(**session_data)

            logger.info(f"Создана сессия Stripe: {session.id}")
            return {
                'success': True,
                'session_id': session.id,
                'checkout_url': session.url,
                'payment_status': session.payment_status
            }

        except stripe.error.StripeError as e:
            logger.error(f"Ошибка создания сессии Stripe: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def retrieve_session(session_id: str) -> Dict:
        """
        Получение информации о сессии оплаты

        Args:
            session_id: ID сессии в Stripe

        Returns:
            Dict с информацией о сессии и статусе платежа
        """
        try:
            session = stripe.checkout.Session.retrieve(session_id)

            logger.info(f"Получена сессия Stripe: {session_id}")
            return {
                'success': True,
                'session_id': session.id,
                'payment_status': session.payment_status,
                'customer_email': session.customer_details.email if session.customer_details else None,
                'amount_total': session.amount_total,
                'currency': session.currency,
                'created': session.created,
                'expires_at': session.expires_at,
                'metadata': session.metadata
            }

        except stripe.error.StripeError as e:
            logger.error(f"Ошибка получения сессии Stripe: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def create_course_payment(course, user, amount: float) -> Dict:
        """
        Создание полного цикла оплаты для курса

        Args:
            course: Объект курса Django
            user: Объект пользователя Django
            amount: Сумма в рублях

        Returns:
            Dict с результатом создания платежа
        """
        try:
            # 1. Создаем продукт
            product_result = StripeService.create_product(
                name=course.title,
                description=course.description
            )

            if not product_result['success']:
                return product_result

            product_id = product_result['product_id']

            # 2. Создаем цену (сумма в копейках)
            amount_in_kopecks = int(amount * 100)
            price_result = StripeService.create_price(
                product_id=product_id,
                amount=amount_in_kopecks
            )

            if not price_result['success']:
                return price_result

            price_id = price_result['price_id']

            # 3. Создаем сессию оплаты
            success_url = f"{settings.FRONTEND_URL}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
            cancel_url = f"{settings.FRONTEND_URL}/payment/cancel"

            # Если нет настроек frontend URL, используем локальные
            if not hasattr(settings, 'FRONTEND_URL'):
                success_url = "http://localhost:3000/payment/success?session_id={CHECKOUT_SESSION_ID}"
                cancel_url = "http://localhost:3000/payment/cancel"

            session_result = StripeService.create_checkout_session(
                price_id=price_id,
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=user.email,
                metadata={
                    'course_id': str(course.id),
                    'user_id': str(user.id),
                    'course_title': course.title
                }
            )

            if not session_result['success']:
                return session_result

            return {
                'success': True,
                'product_id': product_id,
                'price_id': price_id,
                'session_id': session_result['session_id'],
                'checkout_url': session_result['checkout_url'],
                'amount': amount,
                'currency': 'rub'
            }

        except Exception as e:
            logger.error(f"Ошибка создания платежа для курса: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    def create_lesson_payment(lesson, user, amount: float) -> Dict:
        """
        Создание полного цикла оплаты для урока

        Args:
            lesson: Объект урока Django
            user: Объект пользователя Django
            amount: Сумма в рублях

        Returns:
            Dict с результатом создания платежа
        """
        try:
            # 1. Создаем продукт
            product_result = StripeService.create_product(
                name=f"Урок: {lesson.title}",
                description=f"Урок из курса '{lesson.course.title}': {lesson.description}"
            )

            if not product_result['success']:
                return product_result

            product_id = product_result['product_id']

            # 2. Создаем цену (сумма в копейках)
            amount_in_kopecks = int(amount * 100)
            price_result = StripeService.create_price(
                product_id=product_id,
                amount=amount_in_kopecks
            )

            if not price_result['success']:
                return price_result

            price_id = price_result['price_id']

            # 3. Создаем сессию оплаты
            success_url = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
            cancel_url = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/payment/cancel"

            session_result = StripeService.create_checkout_session(
                price_id=price_id,
                success_url=success_url,
                cancel_url=cancel_url,
                customer_email=user.email,
                metadata={
                    'lesson_id': str(lesson.id),
                    'course_id': str(lesson.course.id),
                    'user_id': str(user.id),
                    'lesson_title': lesson.title,
                    'course_title': lesson.course.title
                }
            )

            if not session_result['success']:
                return session_result

            return {
                'success': True,
                'product_id': product_id,
                'price_id': price_id,
                'session_id': session_result['session_id'],
                'checkout_url': session_result['checkout_url'],
                'amount': amount,
                'currency': 'rub'
            }

        except Exception as e:
            logger.error(f"Ошибка создания платежа для урока: {e}")
            return {
                'success': False,
                'error': str(e)
            }