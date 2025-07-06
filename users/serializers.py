from rest_framework import serializers
from .models import User, Payment


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
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'phone', 'city', 'avatar', 'date_joined']


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'city', 'avatar']


# Дополнительное задание - сериализатор пользователя с историей платежей
class UserWithPaymentsSerializer(serializers.ModelSerializer):
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