import re
from urllib.parse import urlparse
from rest_framework import serializers
from django.core.exceptions import ValidationError


def validate_youtube_url(value):
    """
    Валидатор-функция для проверки что ссылка ведет на YouTube.
    Разрешает только ссылки на youtube.com и youtu.be
    """
    if not value:
        return value

    try:
        parsed_url = urlparse(value)
        domain = parsed_url.netloc.lower()

        # Разрешенные домены YouTube
        allowed_domains = [
            'youtube.com',
            'www.youtube.com',
            'youtu.be',
            'www.youtu.be'
        ]

        if domain not in allowed_domains:
            raise ValidationError(
                'Разрешены только ссылки на YouTube (youtube.com или youtu.be)'
            )
    except Exception:
        raise ValidationError('Некорректный формат URL')

    return value


class YouTubeURLValidator:
    """
    Класс-валидатор для проверки ссылок на YouTube.
    Можно использовать в Meta класса сериализатора.
    """

    def __init__(self, field):
        self.field = field

    def __call__(self, attrs):
        value = attrs.get(self.field)
        if value:
            validate_youtube_url(value)
        return attrs


def validate_video_url_content(value):
    """
    Дополнительный валидатор для проверки что ссылка
    ведет именно на видео YouTube (содержит /watch?v= или youtu.be/)
    """
    if not value:
        return value

    youtube_video_patterns = [
        r'youtube\.com/watch\?v=[\w-]+',
        r'youtu\.be/[\w-]+',
        r'youtube\.com/embed/[\w-]+',
        r'youtube\.com/v/[\w-]+'
    ]

    # Проверяем что ссылка соответствует одному из паттернов видео YouTube
    if not any(re.search(pattern, value, re.IGNORECASE) for pattern in youtube_video_patterns):
        raise ValidationError(
            'Ссылка должна вести на конкретное видео YouTube '
            '(например: https://youtube.com/watch?v=VIDEO_ID или https://youtu.be/VIDEO_ID)'
        )

    return value


class VideoContentValidator:
    """
    Класс-валидатор для проверки что ссылка ведет на видео контент YouTube
    """

    def __init__(self, field):
        self.field = field

    def __call__(self, attrs):
        value = attrs.get(self.field)
        if value:
            validate_video_url_content(value)
        return attrs