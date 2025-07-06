from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, Payment


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации пользователя"""
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirm', 'first_name', 'last_name', 'phone', 'city']

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Пароли не совпадают")
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class PaymentSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source='course.title', read_only=True)
    lesson_title = serializers.CharField(source='lesson.title', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    item_title = serializers.ReadOnlyField()
    is_stripe_payment = serializers.ReadOnlyField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)

    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'user_email', 'payment_date', 'updated_at',
            'course', 'course_title', 'lesson', 'lesson_title', 'item_title',
            'amount', 'payment_method', 'payment_method_display',
            'status', 'status_display', 'description',
            'stripe_product_id', 'stripe_price_id', 'stripe_session_id',
            'stripe_checkout_url', 'is_stripe_payment'
        ]
        read_only_fields = [
            'user', 'payment_date', 'updated_at', 'stripe_product_id',
            'stripe_price_id', 'stripe_session_id', 'stripe_checkout_url'
        ]


class StripePaymentCreateSerializer(serializers.Serializer):
    """Сериализатор для создания платежа через Stripe"""
    course_id = serializers.IntegerField(required=False, allow_null=True)
    lesson_id = serializers.IntegerField(required=False, allow_null=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=1)

    def validate(self, attrs):
        course_id = attrs.get('course_id')
        lesson_id = attrs.get('lesson_id')

        if not course_id and not lesson_id:
            raise serializers.ValidationError(
                "Необходимо указать либо course_id, либо lesson_id"
            )

        if course_id and lesson_id:
            raise serializers.ValidationError(
                "Нельзя указывать одновременно course_id и lesson_id"
            )

        return attrs


class StripePaymentResponseSerializer(serializers.Serializer):
    """Сериализатор для ответа при создании Stripe платежа"""
    success = serializers.BooleanField()
    payment = serializers.DictField()
    message = serializers.CharField()


class StripeSessionSerializer(serializers.Serializer):
    """Сериализатор для данных Stripe сессии"""
    session_id = serializers.CharField()
    payment_status = serializers.CharField()
    amount_total = serializers.IntegerField()
    currency = serializers.CharField()
    customer_email = serializers.EmailField(allow_null=True)
    created = serializers.IntegerField()
    expires_at = serializers.IntegerField()


class PaymentStatusResponseSerializer(serializers.Serializer):
    """Сериализатор для ответа при проверке статуса платежа"""
    success = serializers.BooleanField()
    payment = serializers.DictField()
    stripe_data = StripeSessionSerializer()


class UserSerializer(serializers.ModelSerializer):
    """Базовый сериализатор пользователя"""

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'city', 'avatar', 'date_joined']


class UserPrivateSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра своего профиля с приватной информацией"""
    payments = PaymentSerializer(many=True, read_only=True)
    payments_count = serializers.SerializerMethodField()
    stripe_payments_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone', 'city', 'avatar',
            'date_joined', 'payments', 'payments_count', 'stripe_payments_count'
        ]

    def get_payments_count(self, obj):
        return obj.payments.count()

    def get_stripe_payments_count(self, obj):
        return obj.payments.filter(payment_method='stripe').count()


class UserPublicSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра чужого профиля (без приватной информации)"""

    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'phone', 'city', 'avatar', 'date_joined']
        # Исключаем: last_name, payments


class UserUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления профиля"""

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'city', 'avatar']


# Для обратной совместимости
UserWithPaymentsSerializer = UserPrivateSerializer