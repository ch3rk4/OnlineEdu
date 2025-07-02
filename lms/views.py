from rest_framework import viewsets, generics, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Course, Lesson
from .serializers import CourseListSerializer, CourseDetailSerializer, LessonSerializer
from users.permissions import IsModeratorOrOwner


class CourseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsModeratorOrOwner]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'title']
    ordering = ['-created_at']

    def get_queryset(self):
        """
        Возвращает курсы в зависимости от роли пользователя:
        - Модераторы и админы видят все курсы
        - Обычные пользователи видят только свои курсы
        """
        if self.request.user.is_superuser:
            return Course.objects.prefetch_related('lessons')
        elif self.request.user.groups.filter(name='Moderators').exists():
            return Course.objects.prefetch_related('lessons')
        else:
            return Course.objects.filter(owner=self.request.user).prefetch_related('lessons')

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
    serializer_class = LessonSerializer
    permission_classes = [IsAuthenticated, IsModeratorOrOwner]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'description', 'course__title']
    ordering_fields = ['created_at', 'title']
    ordering = ['-created_at']

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