from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from .models import User, Payment
from .serializers import (
    UserSerializer,
    UserUpdateSerializer,
    PaymentSerializer,
    UserWithPaymentsSerializer
)


class PaymentFilter(django_filters.FilterSet):
    """Фильтр для платежей"""
    course = django_filters.NumberFilter(field_name='course__id')
    lesson = django_filters.NumberFilter(field_name='lesson__id')
    payment_method = django_filters.ChoiceFilter(choices=Payment.PAYMENT_METHOD_CHOICES)
    payment_date = django_filters.DateFromToRangeFilter()

    class Meta:
        model = Payment
        fields = ['course', 'lesson', 'payment_method', 'payment_date']


class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с платежами"""
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = PaymentFilter
    ordering_fields = ['payment_date']
    ordering = ['-payment_date']  # По умолчанию сортировка по убыванию даты


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def get_serializer_class(self):
        if self.action == 'retrieve':
            # Для детального просмотра показываем пользователя с историей платежей
            return UserWithPaymentsSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        return UserSerializer