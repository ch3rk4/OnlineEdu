from rest_framework import serializers
from .models import Course, Lesson


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = ['id', 'title', 'description', 'preview', 'video_url', 'course', 'created_at', 'updated_at']


class CourseListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка курсов (без уроков для оптимизации)"""
    lessons_count = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'preview', 'description', 'lessons_count', 'created_at', 'updated_at']

    def get_lessons_count(self, obj):
        return obj.lessons.count()


class CourseDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для детального просмотра курса с уроками"""
    lessons_count = serializers.SerializerMethodField()
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'title', 'preview', 'description', 'lessons_count', 'lessons', 'created_at', 'updated_at']

    def get_lessons_count(self, obj):
        return obj.lessons.count()


# Для обратной совместимости
CourseSerializer = CourseDetailSerializer