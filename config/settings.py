import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'your-secret-key-here'

DEBUG = True

ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third party apps
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',  # Добавляем для blacklist токенов
    'django_filters',
    'drf_spectacular',
    'django_celery_beat',  # ← НОВОЕ: Celery Beat для периодических задач

    # Local apps
    'users',
    'lms',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Europe/Moscow'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PARSER_CLASSES': [
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

# JWT Settings
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'UPDATE_LAST_LOGIN': True,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',

    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'TOKEN_TYPE_CLAIM': 'token_type',
}

# drf-spectacular settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'OnlineEdu API',
    'DESCRIPTION': '''
    Образовательная платформа с курсами, уроками и системой подписок.

    ## Возможности API:

    ### 🔐 Аутентификация
    - JWT токены с автоматическим обновлением
    - Регистрация и авторизация пользователей
    - Система ролей (пользователи, модераторы, администраторы)

    ### 📚 Образовательный контент
    - CRUD операции с курсами и уроками
    - Валидация YouTube ссылок для видео
    - Система подписок на обновления курсов
    - Фильтрация и поиск по контенту

    ### 💳 Платежная система
    - Интеграция со Stripe для приема платежей
    - Создание платежных сессий
    - Отслеживание статуса платежей

    ### 👥 Управление пользователями
    - Профили пользователей с публичной и приватной информацией
    - История платежей пользователей
    - Система прав доступа

    ### 📄 Дополнительные возможности
    - Пагинация для всех списков
    - Подробная фильтрация и сортировка
    - Comprehensive API документация
    ''',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'CONTACT': {
        'name': 'OnlineEdu Support',
        'email': 'support@onlineedu.example.com',
    },
    'LICENSE': {
        'name': 'MIT License',
    },
    'TAGS': [
        {
            'name': 'Authentication',
            'description': 'Регистрация, авторизация и управление JWT токенами'
        },
        {
            'name': 'Courses',
            'description': 'Управление курсами - создание, просмотр, редактирование'
        },
        {
            'name': 'Lessons',
            'description': 'Управление уроками с валидацией YouTube ссылок'
        },
        {
            'name': 'Users',
            'description': 'Управление пользователями и профилями'
        },
        {
            'name': 'Payments',
            'description': 'Платежная система с интеграцией Stripe'
        },
        {
            'name': 'Subscriptions',
            'description': 'Подписки пользователей на обновления курсов'
        },
    ],
    'COMPONENT_SPLIT_REQUEST': True,
    'SORT_OPERATIONS': False,
}

# Custom user model
AUTH_USER_MODEL = 'users.User'

# Frontend URL для Stripe redirect'ов
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:3000')

# Stripe settings
STRIPE_PUBLISHABLE_KEY = os.getenv('STRIPE_PUBLISHABLE_KEY', 'pk_test_...')
STRIPE_SECRET_KEY = os.getenv('STRIPE_SECRET_KEY', 'sk_test_...')
STRIPE_WEBHOOK_SECRET = os.getenv('STRIPE_WEBHOOK_SECRET', 'whsec_...')

# ============================================
# ↓ НОВЫЕ НАСТРОЙКИ CELERY - ДОБАВЬТЕ ЭТО ↓
# ============================================

# Celery Configuration
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = False

# Celery Beat Configuration
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # Для разработки
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'  # Для продакшена
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@onlineedu.com')

# Redis Cache (опционально)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': os.getenv('REDIS_URL', 'redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

"""
Настройки Celery и Redis для асинхронной обработки задач

Эти настройки определяют как Celery будет подключаться к Redis и
как будут обрабатываться асинхронные задачи.
"""

# ===== НАСТРОЙКИ REDIS =====
# Redis используется как брокер сообщений (message broker) для Celery
# Все настройки берем из переменных окружения для безопасности

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', None)

# Формируем URL для подключения к Redis
if REDIS_PASSWORD:
    REDIS_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
else:
    REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

# ===== НАСТРОЙКИ CELERY =====

# Брокер сообщений - где Celery хранит очередь задач
CELERY_BROKER_URL = REDIS_URL

# Где Celery будет сохранять результаты выполнения задач
CELERY_RESULT_BACKEND = REDIS_URL

# Принимаем задачи в формате JSON (безопаснее чем pickle)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Временная зона для задач (должна совпадать с TIME_ZONE)
CELERY_TIMEZONE = TIME_ZONE

# Настройки для celery-beat (планировщик задач)
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# Время жизни результатов задач (7 дней)
CELERY_RESULT_EXPIRES = 60 * 60 * 24 * 7

# ===== НАСТРОЙКИ CELERY-BEAT =====

# Расписание периодических задач
CELERY_BEAT_SCHEDULE = {
    # Задача для блокировки неактивных пользователей
    'block_inactive_users': {
        'task': 'users.tasks.block_inactive_users',
        'schedule': 86400.0,  # Каждые 24 часа (в секундах)
        # Альтернативно можно использовать crontab:
        # 'schedule': crontab(hour=3, minute=0),  # Каждый день в 3:00
    },

    # Пример задачи для очистки старых данных (если понадобится)
    'cleanup_old_data': {
        'task': 'lms.tasks.cleanup_old_data',
        'schedule': 60 * 60 * 24 * 7,  # Раз в неделю
    },
}

# ===== НАСТРОЙКИ EMAIL ДЛЯ РАССЫЛКИ =====

# Настройки для отправки email через Celery
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'OnlineEdu <noreply@onlineedu.com>')

# Настройки для разработки (выводить письма в консоль)
if DEBUG:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# ===== ДОПОЛНИТЕЛЬНЫЕ НАСТРОЙКИ =====

# Логирование для отладки Celery
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'celery.log',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'celery': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}