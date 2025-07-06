from rest_framework import status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiExample
from decimal import Decimal
import logging

from .models import Payment
from .services import StripeService
from .serializers import PaymentSerializer
from lms.models import Course, Lesson

logger = logging.getLogger(__name__)


class CreateStripePaymentView(APIView):
    """
    Создание платежа через Stripe для курса или урока
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Payments'],
        summary='Создание платежа через Stripe',
        description='''
        Создает платеж через Stripe для курса или урока.

        **Процесс:**
        1. Создается продукт в Stripe
        2. Создается цена для продукта
        3. Создается сессия оплаты
        4. Возвращается ссылка на оплату

        **Важно:**
        - Можно оплатить либо курс, либо урок (не оба одновременно)
        - Сумма указывается в рублях с копейками
        - Автоматически создается запись в базе данных
        ''',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'course_id': {
                        'type': 'integer',
                        'description': 'ID курса для оплаты (взаимоисключающе с lesson_id)'
                    },
                    'lesson_id': {
                        'type': 'integer',
                        'description': 'ID урока для оплаты (взаимоисключающе с course_id)'
                    },
                    'amount': {
                        'type': 'string',
                        'description': 'Сумма платежа в рублях (например: "15000.00")'
                    }
                },
                'required': ['amount']
            }
        },
        examples=[
            OpenApiExample(
                name='Оплата курса',
                value={
                    "course_id": 1,
                    "amount": "15000.00"
                }
            ),
            OpenApiExample(
                name='Оплата урока',
                value={
                    "lesson_id": 1,
                    "amount": "2500.00"
                }
            )
        ]
    )
    def post(self, request):
        course_id = request.data.get('course_id')
        lesson_id = request.data.get('lesson_id')
        amount_str = request.data.get('amount')

        # Валидация входных данных
        if not amount_str:
            return Response(
                {"error": "Не указана сумма платежа"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not course_id and not lesson_id:
            return Response(
                {"error": "Необходимо указать либо course_id, либо lesson_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if course_id and lesson_id:
            return Response(
                {"error": "Нельзя указывать одновременно course_id и lesson_id"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            amount = Decimal(amount_str)
            if amount <= 0:
                return Response(
                    {"error": "Сумма должна быть больше нуля"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except (ValueError, TypeError):
            return Response(
                {"error": "Некорректный формат суммы"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Получаем объект курса или урока
        course = None
        lesson = None

        if course_id:
            course = get_object_or_404(Course, id=course_id)
            description = f"Оплата курса: {course.title}"
        else:
            lesson = get_object_or_404(Lesson, id=lesson_id)
            course = lesson.course  # Для метаданных
            description = f"Оплата урока: {lesson.title} (курс: {lesson.course.title})"

        # Создаем платеж в нашей системе
        payment = Payment.objects.create(
            user=request.user,
            course=course if course_id else None,
            lesson=lesson,
            amount=amount,
            payment_method='stripe',
            status='pending',
            description=description
        )

        # Создаем платеж в Stripe
        if course_id:
            stripe_result = StripeService.create_course_payment(
                course=course,
                user=request.user,
                amount=float(amount)
            )
        else:
            stripe_result = StripeService.create_lesson_payment(
                lesson=lesson,
                user=request.user,
                amount=float(amount)
            )

        if not stripe_result['success']:
            # Удаляем созданный платеж если Stripe вернул ошибку
            payment.delete()
            return Response(
                {"error": f"Ошибка создания платежа: {stripe_result['error']}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Обновляем платеж данными из Stripe
        payment.stripe_product_id = stripe_result['product_id']
        payment.stripe_price_id = stripe_result['price_id']
        payment.stripe_session_id = stripe_result['session_id']
        payment.stripe_checkout_url = stripe_result['checkout_url']
        payment.save()

        # Возвращаем данные платежа с ссылкой на оплату
        return Response({
            "success": True,
            "payment": {
                "id": payment.id,
                "amount": str(payment.amount),
                "currency": "RUB",
                "status": payment.status,
                "description": payment.description,
                "checkout_url": payment.stripe_checkout_url,
                "session_id": payment.stripe_session_id,
                "payment_date": payment.payment_date
            },
            "message": "Платеж создан. Перейдите по ссылке checkout_url для оплаты."
        }, status=status.HTTP_201_CREATED)


class StripePaymentStatusView(APIView):
    """
    Проверка статуса платежа через Stripe
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Payments'],
        summary='Проверка статуса платежа',
        description='''
        Получение актуального статуса платежа из Stripe.

        **Возвращает:**
        - Текущий статус платежа в Stripe
        - Обновленную информацию о платеже
        - Данные о сессии оплаты

        **Примечание:** Статус платежа в базе данных автоматически обновляется.
        ''',
        parameters=[
            {
                'name': 'payment_id',
                'in': 'path',
                'description': 'ID платежа в системе',
                'required': True,
                'schema': {'type': 'integer'}
            }
        ]
    )
    def get(self, request, payment_id):
        # Получаем платеж пользователя
        payment = get_object_or_404(
            Payment,
            id=payment_id,
            user=request.user,
            payment_method='stripe'
        )

        if not payment.stripe_session_id:
            return Response(
                {"error": "Платеж не связан с Stripe сессией"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Получаем данные из Stripe
        stripe_result = StripeService.retrieve_session(payment.stripe_session_id)

        if not stripe_result['success']:
            return Response(
                {"error": f"Ошибка получения данных Stripe: {stripe_result['error']}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Обновляем статус платежа
        payment.update_from_stripe_session(stripe_result)

        # Возвращаем обновленные данные
        return Response({
            "success": True,
            "payment": {
                "id": payment.id,
                "amount": str(payment.amount),
                "status": payment.status,
                "description": payment.description,
                "payment_date": payment.payment_date,
                "updated_at": payment.updated_at
            },
            "stripe_data": {
                "session_id": stripe_result['session_id'],
                "payment_status": stripe_result['payment_status'],
                "amount_total": stripe_result['amount_total'],
                "currency": stripe_result['currency'],
                "customer_email": stripe_result['customer_email'],
                "created": stripe_result['created'],
                "expires_at": stripe_result['expires_at']
            }
        })


class StripeWebhookView(APIView):
    """
    Webhook для получения уведомлений от Stripe
    """
    permission_classes = []  # Webhook не требует аутентификации

    @extend_schema(
        tags=['Payments'],
        summary='Webhook Stripe',
        description='''
        Endpoint для получения webhook уведомлений от Stripe.

        **Автоматически обрабатывает:**
        - Успешные платежи
        - Отмененные платежи
        - Возвраты

        **Примечание:** Этот endpoint используется Stripe для уведомлений и не предназначен для прямого вызова.
        ''',
        exclude=True  # Исключаем из документации, так как это внутренний endpoint
    )
    def post(self, request):
        import stripe
        from django.conf import settings

        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            logger.error("Invalid payload in Stripe webhook")
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid signature in Stripe webhook")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        # Обрабатываем события
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            self._handle_successful_payment(session)
        elif event['type'] == 'checkout.session.expired':
            session = event['data']['object']
            self._handle_expired_payment(session)
        else:
            logger.info(f"Unhandled event type: {event['type']}")

        return Response({"received": True})

    def _handle_successful_payment(self, session):
        """Обработка успешного платежа"""
        try:
            payment = Payment.objects.get(stripe_session_id=session['id'])
            payment.status = 'completed'
            payment.save()
            logger.info(f"Payment {payment.id} marked as completed")
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for session {session['id']}")

    def _handle_expired_payment(self, session):
        """Обработка истекшего платежа"""
        try:
            payment = Payment.objects.get(stripe_session_id=session['id'])
            payment.status = 'cancelled'
            payment.save()
            logger.info(f"Payment {payment.id} marked as cancelled")
        except Payment.DoesNotExist:
            logger.error(f"Payment not found for session {session['id']}")


class UserStripePaymentsView(APIView):
    """
    Получение всех Stripe платежей пользователя
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['Payments'],
        summary='Мои Stripe платежи',
        description='''
        Получение списка всех платежей пользователя через Stripe.

        **Фильтрация:** возвращаются только платежи с payment_method='stripe'.
        ''',
        responses={200: PaymentSerializer(many=True)}
    )
    def get(self, request):
        payments = Payment.objects.filter(
            user=request.user,
            payment_method='stripe'
        ).order_by('-payment_date')

        serializer = PaymentSerializer(payments, many=True)
        return Response({
            "payments": serializer.data,
            "count": payments.count()
        })