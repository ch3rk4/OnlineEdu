from rest_framework import viewsets, generics, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from .models import Course, Lesson, Subscription
from .serializers import CourseListSerializer, CourseDetailSerializer, LessonSerializer
from .paginators import CourseLessonPaginator
from users.permissions import IsModeratorOrOwner


@extend_schema_view(
    list=extend_schema(
        tags=['Courses'],
        summary='Список курсов',
        description='''
        Получение списка курсов с пагинацией и фильтрацией.

        **Права доступа:**
        - Обычные пользователи видят только свои курсы
        - Модераторы и админы видят все курсы

        **Включает информацию о подписке** текущего пользователя на каждый курс.

        **Поиск:** используйте параметр `search` для поиска по названию и описанию.
        ''',
        parameters=[
            OpenApiParameter(name='search', type=OpenApiTypes.STR,
                             description='Поиск по названию и описанию курса'),
            OpenApiParameter(name='ordering', type=OpenApiTypes.STR,
                             description='Сортировка: created_at, title'),
        ]
    ),
    create=extend_schema(
        tags=['Courses'],
        summary='Создание курса',
        description='''
        Создание нового курса.

        **Ограничения:**
        - Только обычные пользователи могут создавать курсы
        - Модераторы НЕ могут создавать курсы
        - Создатель автоматически становится владельцем курса
        ''',
        examples=[
            OpenApiExample(
                name='Новый курс',
                value={
                    "title": "Python для начинающих",
                    "description": "Полный курс изучения языка Python с нуля"
                }
            )
        ]
    ),
    retrieve=extend_schema(
        tags=['Courses'],
        summary='Детали курса',
        description='''
        Получение детальной информации о курсе.

        **Включает:**
        - Полную информацию о курсе
        - Список всех уроков курса
        - Статус подписки текущего пользователя
        - Количество уроков
        '''
    ),
    update=extend_schema(
        tags=['Courses'],
        summary='Обновление курса',
        description='''
        Полное обновление курса.

        **Права доступа:**
        - Владелец курса может редактировать
        - Модераторы могут редактировать любые курсы
        '''
    ),
    partial_update=extend_schema(
        tags=['Courses'],
        summary='Частичное обновление курса',
        description='Частичное обновление полей курса.'
    ),
    destroy=extend_schema(
        tags=['Courses'],
        summary='Удаление курса',
        description='''
        Удаление курса.

        **Ограничения:**
        - Только владелец может удалить курс
        - Модераторы НЕ могут удалять курсы
        '''
    )
)
class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    permission_classes = [IsAuthenticated, IsModeratorOrOwner]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'title']
    ordering = ['-created_at']
    pagination_class = CourseLessonPaginator

    def get_queryset(self):
        """
        Возвращает курсы в зависимости от роли пользователя:
        - Модераторы и админы видят все курсы
        - Обычные пользователи видят только свои курсы
        """
        if self.request.user.is_superuser:
            return Course.objects.prefetch_related('lessons', 'subscriptions')
        elif self.request.user.groups.filter(name='Moderators').exists():
            return Course.objects.prefetch_related('lessons', 'subscriptions')
        else:
            return Course.objects.filter(owner=self.request.user).prefetch_related('lessons', 'subscriptions')

    def get_serializer_class(self):
        if self.action == 'list':
            return CourseListSerializer
        elif self.action == 'retrieve':
            return CourseDetailSerializer
        return CourseDetailSerializer

    def perform_create(self, serializer):
        """Автоматически устанавливаем текущего пользователя как владельца курса"""
        serializer.save(owner=self.request.user)

    @extend_schema(
        tags=['Courses'],
        summary='Уроки курса',
        description='''
        Получение всех уроков конкретного курса.

        **Возвращает:** список уроков с полной информацией о каждом уроке.
        ''',
        responses={200: LessonSerializer(many=True)}
    )
    @action(detail=True, methods=['get'])
    def lessons(self, request, pk=None):
        """Получить все уроки конкретного курса"""
        course = self.get_object()
        lessons = course.lessons.all()
        serializer = LessonSerializer(lessons, many=True, context={'request': request})
        return Response(serializer.data)


@extend_schema_view(
    get=extend_schema(
        tags=['Lessons'],
        summary='Список уроков',
        description='''
        Получение списка уроков с пагинацией и фильтрацией.

        **Права доступа:**
        - Обычные пользователи видят только свои уроки
        - Модераторы и админы видят все уроки

        **Поиск:** по названию урока, описанию и названию курса.
        ''',
        parameters=[
            OpenApiParameter(name='search', type=OpenApiTypes.STR,
                             description='Поиск по названию урока, описанию, названию курса'),
            OpenApiParameter(name='ordering', type=OpenApiTypes.STR,
                             description='Сортировка: created_at, title'),
        ]
    ),
    post=extend_schema(
        tags=['Lessons'],
        summary='Создание урока',
        description='''
        Создание нового урока.

        **Валидация видео:**
        - Поддерживаются только ссылки на YouTube
        - Допустимые домены: youtube.com, youtu.be
        - Ссылка должна вести на конкретное видео

        **Ограничения:**
        - Только обычные пользователи могут создавать уроки
        - Модераторы НЕ могут создавать уроки
        ''',
        examples=[
            OpenApiExample(
                name='Новый урок',
                value={
                    "title": "Введение в Python",
                    "description": "Первый урок курса по изучению Python",
                    "video_url": "https://youtube.com/watch?v=abc123",
                    "course": 1
                }
            )
        ]
    )
)
class LessonListCreateView(generics.ListCreateAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsModeratorOrOwner]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'course__title']
    ordering_fields = ['created_at', 'title']
    ordering = ['-created_at']
    pagination_class = CourseLessonPaginator

    def get_queryset(self):
        """
        Возвращает уроки в зависимости от роли пользователя:
        - Модераторы и админы видят все уроки
        - Обычные пользователи видят только свои уроки
        """
        if self.request.user.is_superuser:
            return Lesson.objects.select_related('course', 'owner')
        elif self.request.user.groups.filter(name='Moderators').exists():
            return Lesson.objects.select_related('course', 'owner')
        else:
            return Lesson.objects.filter(owner=self.request.user).select_related('course', 'owner')

    def perform_create(self, serializer):
        """Автоматически устанавливаем текущего пользователя как владельца урока"""
        serializer.save(owner=self.request.user)


@extend_schema_view(
    get=extend_schema(
        tags=['Lessons'],
        summary='Детали урока',
        description='Получение детальной информации об уроке.'
    ),
    put=extend_schema(
        tags=['Lessons'],
        summary='Обновление урока',
        description='''
        Полное обновление урока.

        **Права доступа:**
        - Владелец урока может редактировать
        - Модераторы могут редактировать любые уроки

        **Валидация:** применяется проверка YouTube ссылок.
        '''
    ),
    patch=extend_schema(
        tags=['Lessons'],
        summary='Частичное обновление урока',
        description='Частичное обновление полей урока.'
    ),
    delete=extend_schema(
        tags=['Lessons'],
        summary='Удаление урока',
        description='''
        Удаление урока.

        **Ограничения:**
        - Только владелец может удалить урок
        - Модераторы НЕ могут удалять уроки
        '''
    )
)
class LessonRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Lesson.objects.all()
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsModeratorOrOwner]

    def get_queryset(self):
        """
        Возвращает уроки в зависимости от роли пользователя:
        - Модераторы и админы видят все уроки
        - Обычные пользователи видят только свои уроки
        """
        if self.request.user.is_superuser:
            return Lesson.objects.select_related('course', 'owner')
        elif self.request.user.groups.filter(name='Moderators').exists():
            return Lesson.objects.select_related('course', 'owner')
        else:
            return Lesson.objects.filter(owner=self.request.user).select_related('course', 'owner')


@extend_schema_view(
    post=extend_schema(
        tags=['Subscriptions'],
        summary='Управление подпиской',
        description='''
        Создание или удаление подписки на курс.

        **Логика работы:**
        - Если подписка НЕ существует → создается новая подписка
        - Если подписка существует → удаляется существующая подписка

        **Один запрос для двух действий** - удобно для toggle-кнопок в UI.
        ''',
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'course_id': {
                        'type': 'integer',
                        'description': 'ID курса для подписки'
                    }
                },
                'required': ['course_id']
            }
        },
        examples=[
            OpenApiExample(
                name='Подписка на курс',
                value={"course_id": 1}
            )
        ]
    ),
    get=extend_schema(
        tags=['Subscriptions'],
        summary='Мои подписки',
        description='''
        Получение списка всех подписок текущего пользователя.

        **Возвращает:**
        - Список активных и неактивных подписок
        - Информацию о каждом курсе
        - Даты создания подписок
        '''
    )
)
class SubscriptionAPIView(APIView):
    """
    APIView для управления подписками на курсы.
    POST запрос создает или удаляет подписку в зависимости от текущего состояния.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        course_id = request.data.get('course_id')

        if not course_id:
            return Response(
                {"error": "Не указан ID курса"},
                status=status.HTTP_400_BAD_REQUEST
            )

        course_item = get_object_or_404(Course, id=course_id)

        # Получаем подписку пользователя на этот курс
        subs_item = Subscription.objects.filter(user=user, course=course_item)

        # Если подписка у пользователя на этот курс есть - удаляем ее
        if subs_item.exists():
            subs_item.delete()
            message = 'подписка удалена'
            is_subscribed = False
        # Если подписки у пользователя на этот курс нет - создаем ее
        else:
            Subscription.objects.create(user=user, course=course_item)
            message = 'подписка добавлена'
            is_subscribed = True

        # Возвращаем ответ в API
        return Response({
            "message": message,
            "course_id": str(course_id),
            "course_title": course_item.title,
            "is_subscribed": is_subscribed
        })

    def get(self, request, *args, **kwargs):
        """Получить список всех подписок текущего пользователя"""
        user = request.user
        subscriptions = Subscription.objects.filter(user=user).select_related('course')

        data = []
        for sub in subscriptions:
            data.append({
                'id': sub.id,
                'course_id': sub.course.id,
                'course_title': sub.course.title,
                'created_at': sub.created_at,
                'is_active': sub.is_active
            })

        return Response({
            'subscriptions': data,
            'count': len(data)
        })