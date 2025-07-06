# API Документация OnlineEdu с JWT авторизацией

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

3. Создайте группу модераторов:
```bash
python manage.py create_groups
```

4. Создайте суперпользователя:
```bash
python manage.py createsuperuser
```

5. Загрузите тестовые данные:
```bash
python manage.py init_data
python manage.py load_payments --count 20
```

6. Запустите сервер:
```bash
python manage.py runserver
```

## 🔐 Авторизация

### Регистрация нового пользователя
```
POST /api/auth/register/
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "securepassword",
    "password_confirm": "securepassword",
    "first_name": "Иван",
    "last_name": "Иванов",
    "phone": "+7900123456",
    "city": "Москва"
}
```

### Получение JWT токенов (вход)
```
POST /api/auth/login/
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "securepassword"
}

Ответ:
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "user": {
        "id": 1,
        "email": "user@example.com",
        "first_name": "Иван",
        "last_name": "Иванов"
    }
}
```

### Обновление токена
```
POST /api/auth/refresh/
Content-Type: application/json

{
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
}
```

### Использование токена в запросах
Для всех защищенных endpoints добавляйте заголовок:
```
Authorization: Bearer <access_token>
```

## 👥 Группы пользователей и права доступа

### Обычные пользователи:
- Могут создавать, просматривать, редактировать и удалять **только свои** курсы и уроки
- Могут просматривать любые профили пользователей (без приватной информации)
- Могут редактировать только свой профиль
- Видят только свои платежи

### Модераторы (группа "Moderators"):
- Могут просматривать и редактировать **все** курсы и уроки
- **НЕ могут** создавать и удалять курсы и уроки
- Видят все платежи
- Имеют те же права на профили, что и обычные пользователи

### Администраторы (суперпользователи):
- Полный доступ ко всему

## 📋 API Endpoints

> ⚠️ **Все endpoints (кроме регистрации и авторизации) требуют JWT токен!**

### Авторизация (открытые endpoints)
- **POST /api/auth/register/** - Регистрация
- **POST /api/auth/login/** - Получение токенов
- **POST /api/auth/refresh/** - Обновление токена

### Курсы 🎓
- **GET /api/courses/** - Список курсов (свои для пользователей, все для модераторов)
- **GET /api/courses/{id}/** - Детальная информация о курсе
- **POST /api/courses/** - Создание курса (только не-модераторы)
- **PUT /api/courses/{id}/** - Обновление курса (владелец или модератор)
- **DELETE /api/courses/{id}/** - Удаление курса (только владелец)
- **GET /api/courses/{id}/lessons/** - Получить уроки курса

### Уроки 📚
- **GET /api/lessons/** - Список уроков (свои для пользователей, все для модераторов)
- **GET /api/lessons/{id}/** - Детальная информация об уроке
- **POST /api/lessons/** - Создание урока (только не-модераторы)
- **PUT /api/lessons/{id}/** - Обновление урока (владелец или модератор)
- **DELETE /api/lessons/{id}/** - Удаление урока (только владелец)

### Пользователи 👤
- **GET /api/users/** - Список пользователей
- **GET /api/users/me/** - Мой профиль (с приватной информацией)
- **GET /api/users/{id}/** - Профиль пользователя (публичная информация для чужих)
- **PUT /api/users/{id}/** - Обновление профиля (только свой)
- **GET /api/users/{id}/payments/** - Платежи пользователя (только свои)

### Платежи 💳
- **GET /api/payments/** - Список платежей (свои для пользователей, все для модераторов)
- **GET /api/payments/{id}/** - Детальная информация о платеже
- **POST /api/payments/** - Создание платежа
- **PUT /api/payments/{id}/** - Обновление платежа
- **DELETE /api/payments/{id}/** - Удаление платежа

## 🔍 Фильтрация и поиск

### Платежи:
- `?course=1` - платежи за курс
- `?lesson=1` - платежи за урок
- `?payment_method=cash` - способ оплаты
- `?ordering=-payment_date` - сортировка

### Курсы и уроки:
- `?search=python` - поиск по названию и описанию
- `?ordering=-created_at` - сортировка

### Пользователи:
- `?search=ivan` - поиск по email, имени, фамилии

## 📊 Примеры ответов

### Свой профиль (с приватной информацией):
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
    "payments": [...],
    "payments_count": 5
}
```

### Чужой профиль (только публичная информация):
```json
{
    "id": 2,
    "email": "other@example.com",
    "first_name": "Мария",
    "phone": "+7900654321",
    "city": "СПб",
    "avatar": null,
    "date_joined": "2024-01-01T10:00:00Z"
    // НЕТ: last_name, payments
}
```

### Курс с владельцем:
```json
{
    "id": 1,
    "title": "Python для начинающих",
    "preview": null,
    "description": "Изучение основ Python",
    "lessons_count": 4,
    "owner": 1,
    "owner_email": "user@example.com",
    "lessons": [...],
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T10:00:00Z"
}
```

## 🛡️ Безопасность

### JWT Токены:
- **Access токен**: действует 60 минут
- **Refresh токен**: действует 7 дней
- Автоматическая ротация refresh токенов
- Blacklist отозванных токенов

### Права доступа:
- Строгое разделение между владельцами и модераторами
- Автоматическое назначение владельца при создании объектов
- Скрытие приватной информации в чужих профилях

## 🔧 Администрирование

### Создание модератора:
1. Зайти в админку: `/admin/`
2. Создать пользователя или выбрать существующего
3. Добавить в группу "Moderators"

### Права модераторов в админке:
- Видят все курсы и уроки
- Могут редактировать, но не создавать/удалять
- Ограниченный доступ к форме создания

## 🚀 Пример использования

```bash
# 1. Регистрация
curl -X POST http://localhost:8000/api/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"testpass123","password_confirm":"testpass123"}'

# 2. Получение токена
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"testpass123"}'

# 3. Создание курса (с токеном)
curl -X POST http://localhost:8000/api/courses/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Мой курс","description":"Описание курса"}'

# 4. Просмотр своих курсов
curl -X GET http://localhost:8000/api/courses/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```