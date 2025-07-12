"""
Конфигурация Celery для проекта OnlineEdu

Celery - это асинхронная очередь задач, которая позволяет выполнять
тяжелые операции в фоне, не блокируя основное приложение.
"""
import os
from celery import Celery
from django.conf import settings

# Устанавливаем модуль настроек Django для Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Создаем экземпляр Celery приложения
app = Celery('onlineedu')

# Загружаем конфигурацию из настроек Django
# Все настройки Celery должны начинаться с префикса CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматически обнаруживаем tasks.py в каждом приложении Django
app.autodiscover_tasks()

# Настройки таймзоны - важно для celery-beat
app.conf.timezone = settings.TIME_ZONE

# Конфигурация для результатов задач (опционально)
app.conf.update(
    # Устанавливаем TTL для результатов задач (1 день)
    result_expires=86400,
    # Сжимаем результаты задач для экономии памяти
    result_compression='gzip',
    # Настройки для обработки ошибок
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

@app.task(bind=True)
def debug_task(self):
    """Отладочная задача для проверки работы Celery"""
    print(f'Request: {self.request!r}')
    return 'Celery работает корректно!'