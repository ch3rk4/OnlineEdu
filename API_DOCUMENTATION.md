# API Документация OnlineEdu

## Установка и запуск

1. Установите зависимости:
```bash
pip install -r requirements.txt
```

2. Выполните миграции:
```bash
python manage.py makemigrations
python manage.py migrate
```

3. Создайте суперпользователя:
```bash
python manage.py createsuperuser
```

4. Загрузите тестовые данные платежей (один из вариантов):

### Вариант 1: Через фикстуру
```bash
python manage.py loaddata users/fixtures/payments.json
```

### Вариант 2: Через кастомную команду
```bash
python manage.py load_payments --count 50
```

5. Запустите сервер:
```bash
python manage.py runserver
```

## API Endpoints

### Курсы
- **GET /api/courses/** - Список курсов (с количеством уроков)
- **GET /api/courses/{id}/** - Детальная информация о курсе (с уроками)
- **POST /api/courses/** - Создание курса
- **PUT /api/courses/{id}/** - Обновление курса
- **DELETE /api/courses/{id}/** - Удаление курса
- **GET /api/courses/{id}/lessons/** - Получить уроки курса

### Уроки
- **GET /api/lessons/** - Список уроков
- **GET /api/lessons/{id}/** - Детальная информация об уроке
- **POST /api/lessons/** - Создание урока
- **PUT /api/lessons/{id}/** - Обновление урока
- **DELETE /api/lessons/{id}/** - Удаление урока

### Пользователи
- **GET /api/users/** - Список пользователей
- **GET /api/users/{id}/** - Детальная информация о пользователе (с историей платежей)
- **POST /api/users/** - Создание пользователя
- **PUT /api/users/{id}/** - Обновление пользователя
- **DELETE /api/users/{id}/** - Удаление пользователя

### Платежи
- **GET /api/payments/** - Список платежей (с фильтрацией)
- **GET /api/payments/{id}/** - Детальная информация о платеже
- **POST /api/payments/** - Создание платежа
- **PUT /api/payments/{id}/** - Обновление платежа
- **DELETE /api/payments/{id}/** - Удаление платежа

## Фильтрация платежей

### Параметры фильтрации:
- `course` - ID курса
- `lesson` - ID урока
- `payment_method` - Способ оплаты (`cash` или `transfer`)
- `payment_date_after` - Дата оплаты от (YYYY-MM-DD)
- `payment_date_before` - Дата оплаты до (YYYY-MM-DD)

### Сортировка:
- `ordering` - Сортировка по полю (`payment_date`, `-payment_date`)

### Примеры запросов:

1. Все платежи за курс с ID=1:
```
GET /api/payments/?course=1
```

2. Платежи наличными:
```
GET /api/payments/?payment_method=cash
```

3. Платежи за январь 2024, отсортированные по дате:
```
GET /api/payments/?payment_date_after=2024-01-01&payment_date_before=2024-01-31&ordering=payment_date
```

4. Платежи за урок с ID=5, сортировка по убыванию даты:
```
GET /api/payments/?lesson=5&ordering=-payment_date
```

## Структура ответов

### Курс (детальный просмотр):
```json
{
    "id": 1,
    "title": "Python для начинающих",
    "preview": "http://example.com/media/courses/python.jpg",
    "description": "Изучение основ Python",
    "lessons_count": 5,
    "lessons": [
        {
            "id": 1,
            "title": "Введение",
            "description": "Основы Python",
            "preview": null,
            "video_url": "https://youtube.com/watch?v=example",
            "course": 1,
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:00:00Z"
        }
    ],
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T10:00:00Z"
}
```

### Пользователь (с историей платежей):
```json
{
    "id": 1,
    "email": "user@example.com",
    "first_name": "Иван",
    "last_name": "Иванов",
    "phone": "+7900123456",
    "city": "Москва",
    "avatar": null,
    "date_joined": "2024-01-01T10:00:00Z",
    "payments": [
        {
            "id": 1,
            "user": 1,
            "user_email": "user@example.com",
            "payment_date": "2024-01-15T10:30:00Z",
            "course": 1,
            "course_title": "Python для начинающих",
            "lesson": null,
            "lesson_title": null,
            "amount": "15000.00",
            "payment_method": "transfer"
        }
    ],
    "payments_count": 1
}
```

### Платеж:
```json
{
    "id": 1,
    "user": 1,
    "user_email": "user@example.com",
    "payment_date": "2024-01-15T10:30:00Z",
    "course": 1,
    "course_title": "Python для начинающих",
    "lesson": null,
    "lesson_title": null,
    "amount": "15000.00",
    "payment_method": "transfer"
}
```

## Админка

Доступна по адресу `/admin/` со следующими возможностями:

### Курсы:
- Просмотр списка курсов с количеством уроков
- Редактирование курсов с inline редактированием уроков
- Фильтрация по дате создания
- Поиск по названию и описанию

### Платежи:
- Просмотр списка платежей с информацией об оплаченном элементе
- Фильтрация по способу оплаты, дате, курсу, уроку
- Поиск по email пользователя, названию курса/урока
- Иерархия по дате платежа

### Пользователи:
- Кастомная модель пользователя с email вместо username
- Редактирование профиля пользователя
- Фильтрация по статусу и городу