from rest_framework import viewsets, filters, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from .models import User, Payment
from .serializers import (
    UserSerializer,
    UserUpdateSerializer,
    PaymentSerializer,
    UserPrivateSerializer,
    UserPublicSerializer,
    UserRegistrationSerializer
)
from .permissions import IsOwnerOrReadOnly


class UserRegistrationView(generics.CreateAPIView):
    """Регистрация нового пользователя"""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "message": "Пользователь успешно зарегистрирован",
                "user": UserSerializer(user).data
            },
            status=status.HTTP_201_CREATED
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    """Кастомный view для получения JWT токенов"""
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            # Добавляем информацию о пользователе в ответ
            try:
                user = User.objects.get(email=request.data.get('email'))
                response.data['user'] = UserSerializer(user).data
            except User.DoesNotExist:
                pass
        return response


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
    # Базовый queryset для роутера
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = PaymentFilter
    ordering_fields = ['payment_date']
    ordering = ['-payment_date']

    def get_queryset(self):
        """Пользователи видят только свои платежи, модераторы и админы - все"""
        if self.request.user.is_superuser:
            return Payment.objects.all()
        elif self.request.user.groups.filter(name='Moderators').exists():
            return Payment.objects.all()
        else:
            return Payment.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Автоматически устанавливаем текущего пользователя как владельца платежа"""
        serializer.save(user=self.request.user)


class UserViewSet(viewsets.ModelViewSet):
    # Базовый queryset для роутера
    queryset = User.objects.all()
    permission_classes = [IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'email']
    ordering = ['-date_joined']

    def get_serializer_class(self):
        """Выбираем сериализатор в зависимости от действия и пользователя"""
        if self.action == 'create':
            return UserRegistrationSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        elif self.action == 'retrieve':
            # Для детального просмотра
            user = self.get_object()
            if user == self.request.user:
                # Свой профиль - показываем все
                return UserPrivateSerializer
            else:
                # Чужой профиль - только публичную информацию
                return UserPublicSerializer
        return UserSerializer

    def get_queryset(self):
        """Возвращаем queryset с оптимизацией для платежей"""
        if self.action == 'retrieve' and hasattr(self, 'get_object'):
            # Для детального просмотра подгружаем платежи только для своего профиля
            try:
                user = self.get_object()
                if user == self.request.user:
                    return User.objects.prefetch_related('payments').all()
            except:
                pass
        return User.objects.all()

    @action(detail=True, methods=['get'])
    def payments(self, request, pk=None):
        """Получить платежи пользователя (только для своего профиля)"""
        user = self.get_object()
        if user != request.user and not request.user.is_superuser:
            return Response(
                {"detail": "Вы можете просматривать только свои платежи"},
                status=status.HTTP_403_FORBIDDEN
            )

        payments = user.payments.all()
        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def me(self, request):
        """Получить информацию о текущем пользователе"""
        serializer = UserPrivateSerializer(request.user)
        return Response(serializer.data)