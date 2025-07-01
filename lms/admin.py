from django.contrib import admin
from .models import Course, Lesson


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 0
    fields = ('title', 'video_url')


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at', 'lessons_count')
    list_filter = ('created_at',)
    search_fields = ('title', 'description')
    inlines = [LessonInline]

    def lessons_count(self, obj):
        return obj.lessons.count()
    lessons_count.short_description = 'Количество уроков'


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'course', 'created_at')
    list_filter = ('course', 'created_at')
    search_fields = ('title', 'description', 'course__title')