from django.db.migrations import serializer
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
from .tasks import process_course_update_notification, process_lesson_update_notification, logger
import logging

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

    def perform_update(self, serializer):
        """
        Переопределяем метод обновления курса для запуска уведомлений

        Этот метод вызывается Django REST Framework при PUT/PATCH запросах.
        Мы перехватываем момент сохранения, чтобы запустить асинхронные уведомления.
        """
        # Сохраняем информацию о курсе до обновления
        course = self.get_object()
        old_title = course.title
        old_description = course.description

        # Выполняем стандартное обновление
        updated_course = serializer.save()

        # Определяем тип изменений для более точных уведомлений
        changes = []
        if old_title != updated_course.title:
            changes.append('title')
        if old_description != updated_course.description:
            changes.append('description')

        # Проверяем, нужно ли отправлять уведомления
        can_notify, reason = updated_course.can_send_notification()

        if can_notify:
            # Запускаем асинхронную задачу уведомления
            # .delay() означает "выполни эту задачу в фоне, не блокируя текущий запрос"
            try:
                process_course_update_notification.delay(
                    course_id=updated_course.id,
                    update_type='general'
                )

                logger.info(
                    f"Запущена задача уведомления для курса {updated_course.title} "
                    f"(изменения: {changes})"
                )

            except Exception as e:
                # Если не удалось запустить задачу - логируем, но не прерываем основной процесс
                logger.error(f"Ошибка запуска уведомления для курса {updated_course.id}: {e}")
        else:
            logger.info(f"Уведомление для курса {updated_course.title} пропущено: {reason}")

    def perform_create(self, serializer):
        """
        Переопределяем создание курса

        При создании нового курса обычно не отправляем уведомления,
        но можно добавить логику для уведомления админов или аналитики.
        """
        # Стандартное создание с назначением владельца
        course = serializer.save(owner=self.request.user)

        # Опционально: уведомление админов о новом курсе
        logger.info(f"Создан новый курс: {course.title} пользователем {self.request.user.email}")

        # Можно добавить задачу для аналитики
        # from .tasks import track_course_creation
        # track_course_creation.delay(course.id, self.request.user.id)

    @action(detail=True, methods=['post'])
    def toggle_notifications(self, request, pk=None):
        """
        Кастомное действие для включения/отключения уведомлений курса

        Позволяет владельцам курсов управлять уведомлениями через API:
        POST /api/courses/{id}/toggle_notifications/
        """
        course = self.get_object()

        # Переключаем статус уведомлений
        course.notification_enabled = not course.notification_enabled
        course.save(update_fields=['notification_enabled'])

        status_text = "включены" if course.notification_enabled else "отключены"

        return Response({
            'message': f'Уведомления для курса "{course.title}" {status_text}',
            'notification_enabled': course.notification_enabled,
            'notification_stats': course.get_notification_stats()
        })

    @action(detail=True, methods=['get'])
    def notification_stats(self, request, pk=None):
        """
        Получение статистики уведомлений для курса

        GET /api/courses/{id}/notification_stats/
        """
        course = self.get_object()
        stats = course.get_notification_stats()

        return Response({
            'course_id': course.id,
            'course_title': course.title,
            'stats': stats
        })

    @action(detail=True, methods=['post'])
    def force_notification(self, request, pk=None):
        """
        Принудительная отправка уведомления (для владельцев и админов)

        POST /api/courses/{id}/force_notification/
        Полезно для тестирования или срочных обновлений
        """
        course = self.get_object()

        # Проверяем права (только владелец или админ)
        if course.owner != request.user and not request.user.is_superuser:
            return Response(
                {'error': 'Только владелец курса может принудительно отправить уведомление'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Запускаем уведомление независимо от временных ограничений
        try:
            from users.tasks import send_bulk_course_notifications

            # Обновляем время последнего уведомления
            from django.utils import timezone
            course.last_notification_sent = timezone.now()
            course.save(update_fields=['last_notification_sent'])

            # Запускаем задачу
            task = send_bulk_course_notifications.delay(
                course_id=course.id,
                course_title=course.title,
                update_type='forced'
            )

            return Response({
                'message': f'Принудительное уведомление запущено для курса "{course.title}"',
                'task_id': task.id,
                'subscriber_count': course.subscriptions.filter(is_active=True).count()
            })

        except Exception as e:
            logger.error(f"Ошибка принудительного уведомления для курса {course.id}: {e}")
            return Response(
                {'error': f'Ошибка запуска уведомления: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
        lesson = serializer.save(owner=self.request.user)

        # Уведомляем подписчиков о новом уроке
        course = lesson.course
        can_notify, reason = course.can_send_notification()

        if can_notify:
            try:
                process_lesson_update_notification.delay(
                    lesson_id=lesson.id,
                    update_type='new_lesson'
                )

                logger.info(
                    f"Запущена задача уведомления о новом уроке {lesson.title} "
                    f"в курсе {course.title}"
                )

            except Exception as e:
                logger.error(f"Ошибка запуска уведомления о новом уроке {lesson.id}: {e}")
        else:
            logger.info(f"Уведомление о новом уроке {lesson.title} пропущено: {reason}")


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

    def perform_update(self, serializer):
        """
        Переопределяем обновление урока для запуска уведомлений

        Логика похожа на курсы, но учитываем, что урок является частью курса.
        """
        # Получаем урок до изменений
        lesson = self.get_object()
        old_title = lesson.title
        old_description = lesson.description
        old_video_url = lesson.video_url

        # Выполняем обновление
        updated_lesson = serializer.save()

        # Определяем значимость изменений
        significant_changes = []
        if old_title != updated_lesson.title:
            significant_changes.append('title')
        if old_video_url != updated_lesson.video_url:
            significant_changes.append('video')  # Смена видео - важное изменение
        if old_description != updated_lesson.description:
            significant_changes.append('description')

        # Если есть значимые изменения - отправляем уведомления
        if significant_changes:
            course = updated_lesson.course
            can_notify, reason = course.can_send_notification()

            if can_notify:
                try:
                    # Запускаем уведомление об обновлении урока
                    process_lesson_update_notification.delay(
                        lesson_id=updated_lesson.id,
                        update_type='lesson_updated'
                    )

                    logger.info(
                        f"Запущена задача уведомления об обновлении урока {updated_lesson.title} "
                        f"в курсе {course.title} (изменения: {significant_changes})"
                    )

                except Exception as e:
                    logger.error(f"Ошибка запуска уведомления для урока {updated_lesson.id}: {e}")
            else:
                logger.info(
                    f"Уведомление об уроке {updated_lesson.title} пропущено: {reason}"
                )
        else:
            logger.info(f"Незначимые изменения урока {updated_lesson.title} - уведомления не отправляем")


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