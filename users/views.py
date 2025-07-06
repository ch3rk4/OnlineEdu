from rest_framework import viewsets, filters, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as django_filters
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
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
from lms.paginators import UserPaginator, PaymentPaginator


@extend_schema(
    tags=['Authentication'],
    summary='Регистрация нового пользователя',
    description='''
    Создает нового пользователя в системе.

    **Требования к паролю:**
    - Минимум 8 символов
    - Не должен быть слишком простым
    - Не должен состоять только из цифр

    **Поля email уникальны** - нельзя зарегистрировать два аккаунта с одинаковым email.
    ''',
    examples=[
        OpenApiExample(
            name='Успешная регистрация',
            value={
                "email": "student@example.com",
                "password": "securepassword123",
                "password_confirm": "securepassword123",
                "first_name": "Иван",
                "last_name": "Петров",
                "phone": "+7900123456",
                "city": "Москва"
            }
        )
    ]
)
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


@extend_schema(
    tags=['Authentication'],
    summary='Получение JWT токенов',
    description='''
    Аутентификация пользователя и получение пары JWT токенов.

    **Возвращает:**
    - `access` - токен доступа (действует 60 минут)
    - `refresh` - токен обновления (действует 7 дней)
    - `user` - информация о пользователе

    **Access токен** используется для доступа к защищенным endpoints.
    **Refresh токен** используется для получения нового access токена.
    ''',
    examples=[
        OpenApiExample(
            name='Успешная авторизация',
            value={
                "email": "student@example.com",
                "password": "securepassword123"
            }
        )
    ]
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


@extend_schema_view(
    list=extend_schema(
        tags=['Payments'],
        summary='Список платежей',
        description='''
        Получение списка платежей с возможностью фильтрации.

        **Права доступа:**
        - Обычные пользователи видят только свои платежи
        - Модераторы и админы видят все платежи

        **Доступная фильтрация:**
        - По курсу: `?course=1`
        - По уроку: `?lesson=1` 
        - По способу оплаты: `?payment_method=cash`
        - По дате: `?payment_date_after=2024-01-01&payment_date_before=2024-12-31`
        - Сортировка: `?ordering=-payment_date`
        ''',
        parameters=[
            OpenApiParameter(name='course', type=OpenApiTypes.INT, description='ID курса'),
            OpenApiParameter(name='lesson', type=OpenApiTypes.INT, description='ID урока'),
            OpenApiParameter(name='payment_method', type=OpenApiTypes.STR,
                             enum=['cash', 'transfer'], description='Способ оплаты'),
            OpenApiParameter(name='ordering', type=OpenApiTypes.STR,
                             description='Сортировка по полю (добавьте - для убывания)'),
        ]
    ),
    create=extend_schema(
        tags=['Payments'],
        summary='Создание платежа',
        description='''
        Создание нового платежа в системе.

        **Примечания:**
        - Пользователь автоматически устанавливается как владелец платежа
        - Можно оплатить либо курс, либо урок (но не оба одновременно)
        - Сумма указывается в рублях с копейками
        ''',
        examples=[
            OpenApiExample(
                name='Оплата курса',
                value={
                    "course": 1,
                    "amount": "15000.00",
                    "payment_method": "transfer"
                }
            ),
            OpenApiExample(
                name='Оплата урока',
                value={
                    "lesson": 1,
                    "amount": "2500.00",
                    "payment_method": "cash"
                }
            )
        ]
    )
)
class PaymentViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с платежами"""
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = PaymentFilter
    ordering_fields = ['payment_date']
    ordering = ['-payment_date']
    pagination_class = PaymentPaginator

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


@extend_schema_view(
    list=extend_schema(
        tags=['Users'],
        summary='Список пользователей',
        description='''
        Получение списка всех пользователей с пагинацией.

        **Возвращается только публичная информация** о пользователях:
        - email, first_name, phone, city, avatar, date_joined
        - НЕ возвращается: last_name, пароль, платежи

        **Поиск:** используйте параметр `search` для поиска по email, имени, фамилии.
        ''',
        parameters=[
            OpenApiParameter(name='search', type=OpenApiTypes.STR,
                             description='Поиск по email, имени, фамилии'),
            OpenApiParameter(name='ordering', type=OpenApiTypes.STR,
                             description='Сортировка: date_joined, email'),
        ]
    ),
    retrieve=extend_schema(
        tags=['Users'],
        summary='Детали пользователя',
        description='''
        Получение детальной информации о пользователе.

        **Логика отображения:**
        - **Свой профиль:** полная информация включая last_name и платежи
        - **Чужой профиль:** только публичная информация
        ''',
    ),
    update=extend_schema(
        tags=['Users'],
        summary='Обновление профиля',
        description='Обновление своего профиля. Нельзя редактировать чужие профили.'
    ),
    partial_update=extend_schema(
        tags=['Users'],
        summary='Частичное обновление профиля',
        description='Частичное обновление своего профиля.'
    )
)
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsOwnerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'email']
    ordering = ['-date_joined']
    pagination_class = UserPaginator

    def get_serializer_class(self):
        """Выбираем сериализатор в зависимости от действия и пользователя"""
        if self.action == 'create':
            return UserRegistrationSerializer
        elif self.action in ['update', 'partial_update']:
            return UserUpdateSerializer
        elif self.action == 'retrieve':
            user = self.get_object()
            if user == self.request.user:
                return UserPrivateSerializer
            else:
                return UserPublicSerializer
        return UserSerializer

    def get_queryset(self):
        """Возвращаем queryset с оптимизацией для платежей"""
        if self.action == 'retrieve' and hasattr(self, 'get_object'):
            try:
                user = self.get_object()
                if user == self.request.user:
                    return User.objects.prefetch_related('payments').all()
            except:
                pass
        return User.objects.all()

    @extend_schema(
        tags=['Users'],
        summary='Платежи пользователя',
        description='''
        Получение списка платежей конкретного пользователя.

        **Ограничения доступа:**
        - Можно просматривать только свои платежи
        - Администраторы могут просматривать любые платежи
        ''',
        responses={200: PaymentSerializer(many=True)}
    )
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
        paginator = PaymentPaginator()
        page = paginator.paginate_queryset(payments, request)
        if page is not None:
            serializer = PaymentSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = PaymentSerializer(payments, many=True)
        return Response(serializer.data)

    @extend_schema(
        tags=['Users'],
        summary='Мой профиль',
        description='''
        Получение полной информации о своем профиле.

        **Включает:**
        - Всю личную информацию (включая last_name)
        - Список всех платежей
        - Количество платежей
        ''',
        responses={200: UserPrivateSerializer}
    )
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Получить информацию о текущем пользователе"""
        serializer = UserPrivateSerializer(request.user)
        return Response(serializer.data)