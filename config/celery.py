import os
from celery import Celery
from django.conf import settings

# Устанавливаем переменную окружения для Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('onlineedu')

# Используем настройки Django для Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автоматическое обнаружение задач в приложениях Django
app.autodiscover_tasks()

# Конфигурация для celery-beat (периодические задачи)
app.conf.beat_schedule = {
    'deactivate-inactive-users': {
        'task': 'users.tasks.deactivate_inactive_users',
        'schedule': 3600.0,  # Каждый час (можно настроить по потребности)
        # 'schedule': crontab(hour=2, minute=0),  # Каждый день в 2:00
    },
}

# Часовой пояс для задач
app.conf.timezone = settings.TIME_ZONE

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Отладочная задача для тестирования Celery"""
    print(f'Request: {self.request!r}')