# OnlineEdu - Образовательная платформа

Django REST API приложение с курсами, уроками, платежами и уведомлениями.

## Быстрый старт

### 1. Настройка переменных окружения

```bash
cp .env.example .env
```

Отредактируйте `.env` файл под ваши нужды.

### 2. Запуск проекта

```bash
# Запуск всех сервисов
docker-compose up -d --build

# Применение миграций
docker-compose exec web python manage.py migrate

# Создание суперпользователя
docker-compose exec web python manage.py createsuperuser

# Создание групп пользователей
docker-compose exec web python manage.py create_groups
```

### 3. Проверка работоспособности

- **Приложение**: http://localhost
- **API документация**: http://localhost/api/docs/
- **Админ панель**: http://localhost/admin/

## Сервисы

| Сервис | Описание | Порт |
|--------|----------|------|
| web | Django + Gunicorn | 8000 |
| db | PostgreSQL 15 | 5432 |
| redis | Redis 7 | 6379 |
| celery-worker | Celery worker | - |
| celery-beat | Celery scheduler | - |
| nginx | Reverse proxy | 80, 443 |

## Полезные команды

```bash
# Просмотр логов
docker-compose logs -f

# Остановка сервисов
docker-compose down

# Перезапуск
docker-compose restart

# Выполнение команд Django
docker-compose exec web python manage.py <command>

# Подключение к базе данных
docker-compose exec db psql -U postgres onlineedu

# Тесты
docker-compose exec web python manage.py test
```

## Проверка сервисов

### База данных
```bash
docker-compose exec db psql -U postgres onlineedu -c "\dt"
```

### Redis
```bash
docker-compose exec redis redis-cli ping
```

### Celery
```bash
docker-compose exec celery-worker celery -A config status
```

## Настройка удаленного сервера

### Требования
- Ubuntu 20.04+
- Docker и Docker Compose
- 2GB RAM, 20GB диск

### Установка на сервере

1. **Обновление системы**
```bash
sudo apt update && sudo apt upgrade -y
```

2. **Установка Docker**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

3. **Установка Docker Compose**
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

4. **Клонирование проекта**
```bash
git clone <repository-url>
cd onlineedu
cp .env.example .env
# Настройте .env для продакшена
```

5. **Запуск**
```bash
docker-compose up -d --build
docker-compose exec web python manage.py migrate
```

## GitHub Actions

Для автоматического деплоя настройте в Settings → Secrets:

- `SERVER_HOST` - IP сервера
- `SERVER_USER` - пользователь для SSH
- `SERVER_SSH_KEY` - приватный SSH ключ
- `SERVER_PORT` - SSH порт (обычно 22)
- `PRODUCTION_URL` - URL продакшен сайта

Push в `main` ветку автоматически запустит деплой на сервер.