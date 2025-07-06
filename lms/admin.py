from django.contrib import admin
from .models import Course, Lesson


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ('title', 'video_url', 'owner')
    readonly_fields = ('owner',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'created_at', 'lessons_count')
    list_filter = ('created_at', 'owner')
    search_fields = ('title', 'description', 'owner__email')
    inlines = [LessonInline]
    autocomplete_fields = ['owner']
    readonly_fields = ('created_at', 'updated_at')

    def lessons_count(self, obj):
        return obj.lessons.count()
    lessons_count.short_description = 'Количество уроков'

    def get_queryset(self, request):
        """Показываем курсы в зависимости от роли пользователя"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        elif request.user.groups.filter(name='Moderators').exists():
            return qs  # Модераторы видят все курсы
        else:
            return qs.filter(owner=request.user)  # Обычные пользователи только свои

    def has_add_permission(self, request):
        """Модераторы не могут создавать курсы"""
        if request.user.is_superuser:
            return True
        return not request.user.groups.filter(name='Moderators').exists()

    def has_delete_permission(self, request, obj=None):
        """Модераторы не могут удалять курсы"""
        if request.user.is_superuser:
            return True
        is_moderator = request.user.groups.filter(name='Moderators').exists()
        if is_moderator:
            return False
        # Обычные пользователи могут удалять только свои курсы
        if obj:
            return obj.owner == request.user
        return True


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'owner', 'created_at')
    list_filter = ('course', 'created_at', 'owner')
    search_fields = ('title', 'description', 'course__title', 'owner__email')
    autocomplete_fields = ['course', 'owner']
    readonly_fields = ('created_at', 'updated_at')

    def get_queryset(self, request):
        """Показываем уроки в зависимости от роли пользователя"""
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        elif request.user.groups.filter(name='Moderators').exists():
            return qs  # Модераторы видят все уроки
        else:
            return qs.filter(owner=request.user)  # Обычные пользователи только свои

    def has_add_permission(self, request):
        """Модераторы не могут создавать уроки"""
        if request.user.is_superuser:
            return True
        return not request.user.groups.filter(name='Moderators').exists()

    def has_delete_permission(self, request, obj=None):
        """Модераторы не могут удалять уроки"""
        if request.user.is_superuser:
            return True
        is_moderator = request.user.groups.filter(name='Moderators').exists()
        if is_moderator:
            return False
        # Обычные пользователи могут удалять только свои уроки
        if obj:
            return obj.owner == request.user
        return True

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """Ограничиваем выбор курсов для уроков"""
        if db_field.name == "course":
            if request.user.is_superuser:
                pass  # Суперпользователь видит все курсы
            elif request.user.groups.filter(name='Moderators').exists():
                pass  # Модераторы видят все курсы
            else:
                kwargs["queryset"] = Course.objects.filter(owner=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)