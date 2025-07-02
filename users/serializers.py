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

    class Meta:
        model = Payment
        fields = [
            'id', 'user', 'user_email', 'payment_date', 'course', 'course_title',
            'lesson', 'lesson_title', 'amount', 'payment_method'
        ]


class UserSerializer(serializers.ModelSerializer):
    """Базовый сериализатор пользователя"""
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'city', 'avatar', 'date_joined']


class UserPrivateSerializer(serializers.ModelSerializer):
    """Сериализатор для просмотра своего профиля с приватной информацией"""
    payments = PaymentSerializer(many=True, read_only=True)
    payments_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'phone', 'city', 'avatar',
            'date_joined', 'payments', 'payments_count'
        ]

    def get_payments_count(self, obj):
        return obj.payments.count()


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