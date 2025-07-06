from rest_framework import serializers
from .models import Course, Lesson
from .validators import validate_youtube_url, validate_video_url_content, YouTubeURLValidator


class LessonSerializer(serializers.ModelSerializer):
    owner_email = serializers.CharField(source='owner.email', read_only=True)
    # Добавляем валидаторы для поля video_url
    video_url = serializers.URLField(
        validators=[validate_youtube_url, validate_video_url_content]
    )

    class Meta:
        model = Lesson
        fields = ['id', 'title', 'description', 'preview', 'video_url', 'course', 'owner', 'owner_email', 'created_at',
                  'updated_at']
        read_only_fields = ['owner']
        # Альтернативный способ добавления валидаторов через Meta
        validators = [
            YouTubeURLValidator(field='video_url')
        ]

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class CourseListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка курсов (без уроков для оптимизации)"""
    lessons_count = serializers.SerializerMethodField()
    owner_email = serializers.CharField(source='owner.email', read_only=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'preview', 'description', 'lessons_count', 'owner', 'owner_email',
                  'is_subscribed', 'created_at', 'updated_at']
        read_only_fields = ['owner']

    def get_lessons_count(self, obj):
        return obj.lessons.count()

    def get_is_subscribed(self, obj):
        """Проверяем подписан ли текущий пользователь на курс"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.subscriptions.filter(user=request.user).exists()
        return False

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


class CourseDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для детального просмотра курса с уроками"""
    lessons_count = serializers.SerializerMethodField()
    lessons = LessonSerializer(many=True, read_only=True)
    owner_email = serializers.CharField(source='owner.email', read_only=True)
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = ['id', 'title', 'preview', 'description', 'lessons_count', 'lessons', 'owner', 'owner_email',
                  'is_subscribed', 'created_at', 'updated_at']
        read_only_fields = ['owner']

    def get_lessons_count(self, obj):
        return obj.lessons.count()

    def get_is_subscribed(self, obj):
        """Проверяем подписан ли текущий пользователь на курс"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.subscriptions.filter(user=request.user).exists()
        return False

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)


# Для обратной совместимости
CourseSerializer = CourseDetailSerializer