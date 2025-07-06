from rest_framework import viewsets, generics, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Course, Lesson, Subscription
from .serializers import CourseListSerializer, CourseDetailSerializer, LessonSerializer
from .paginators import CourseLessonPaginator
from users.permissions import IsModeratorOrOwner


class CourseViewSet(viewsets.ModelViewSet):
    # Базовый queryset для роутера
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

    @action(detail=True, methods=['get'])
    def lessons(self, request, pk=None):
        """Получить все уроки конкретного курса"""
        course = self.get_object()
        lessons = course.lessons.all()
        serializer = LessonSerializer(lessons, many=True, context={'request': request})
        return Response(serializer.data)


class LessonListCreateView(generics.ListCreateAPIView):
    # Базовый queryset
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


class LessonRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    # Базовый queryset
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
        # Если подписки у пользователя на этот курс нет - создаем ее
        else:
            Subscription.objects.create(user=user, course=course_item)
            message = 'подписка добавлена'

        # Возвращаем ответ в API
        return Response({
            "message": message,
            "course_id": course_id,
            "course_title": course_item.title,
            "is_subscribed": not subs_item.exists()  # Новое состояние подписки
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