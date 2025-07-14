# Используем официальный образ Python 3.13
FROM python:3.13-slim

# Устанавливаем переменные окружения для Python
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Создаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        curl \
        && rm -rf /var/lib/apt/lists/*

# Устанавливаем Poetry
RUN pip install poetry

# Копируем файлы Poetry
COPY pyproject.toml poetry.lock ./

# Конфигурируем Poetry
RUN poetry config virtualenvs.create false \
    && poetry install --no-dev --no-interaction --no-ansi

# Копируем код приложения
COPY . .

# Создаем директории для статических файлов и медиа
RUN mkdir -p /app/staticfiles /app/media

# Создаем пользователя для безопасности
RUN adduser --disabled-password --gecos '' appuser \
    && chown -R appuser:appuser /app
USER appuser

# Устанавливаем порт
EXPOSE 8000

# Создаем скрипт для запуска
COPY --chown=appuser:appuser docker-entrypoint.sh /app/
RUN chmod +x /app/docker-entrypoint.sh

# Команда по умолчанию
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn"]