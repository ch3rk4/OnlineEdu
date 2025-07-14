#!/bin/bash

set -e

# Функция для ожидания доступности базы данных
wait_for_db() {
    echo "Waiting for database..."
    while ! pg_isready -h "${DB_HOST:-db}" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}"; do
        sleep 1
    done
    echo "Database is ready!"
}

# Функция для ожидания Redis
wait_for_redis() {
    echo "Waiting for Redis..."
    until redis-cli -h "${REDIS_HOST:-redis}" -p "${REDIS_PORT:-6379}" ping; do
        sleep 1
    done
    echo "Redis is ready!"
}

# Применяем миграции и собираем статику
setup_django() {
    echo "Setting up Django..."
    python manage.py migrate --no-input
    python manage.py collectstatic --no-input --clear

    # Создаем группы если их нет
    python manage.py create_groups || true

    echo "Django setup completed!"
}

case "$1" in
    gunicorn)
        wait_for_db
        setup_django
        echo "Starting Gunicorn..."
        exec gunicorn config.wsgi:application \
            --bind 0.0.0.0:8000 \
            --workers 3 \
            --timeout 120 \
            --access-logfile - \
            --error-logfile -
        ;;
    celery-worker)
        wait_for_db
        wait_for_redis
        echo "Starting Celery Worker..."
        exec celery -A config worker -l info --concurrency=2
        ;;
    celery-beat)
        wait_for_db
        wait_for_redis
        echo "Starting Celery Beat..."
        exec celery -A config beat -l info \
            --scheduler django_celery_beat.schedulers:DatabaseScheduler
        ;;
    manage)
        wait_for_db
        shift
        echo "Running Django management command: $@"
        exec python manage.py "$@"
        ;;
    shell)
        wait_for_db
        echo "Starting Django shell..."
        exec python manage.py shell
        ;;
    test)
        wait_for_db
        echo "Running tests..."
        exec python manage.py test
        ;;
    *)
        echo "Available commands:"
        echo "  gunicorn - Start Gunicorn server"
        echo "  celery-worker - Start Celery worker"
        echo "  celery-beat - Start Celery beat scheduler"
        echo "  manage <command> - Run Django management command"
        echo "  shell - Start Django shell"
        echo "  test - Run tests"
        exit 1
        ;;
esac