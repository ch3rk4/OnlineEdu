from django.core.management.base import BaseCommand
from lms.models import Course, Lesson
from users.models import User


class Command(BaseCommand):
    help = 'Инициализирует базу данных тестовыми данными'

    def handle(self, *args, **options):
        self.stdout.write('Создание тестовых данных...')

        # Создаем пользователей, если их нет
        if not User.objects.exists():
            users_data = [
                {
                    'email': 'student1@example.com',
                    'password': 'password123',
                    'first_name': 'Иван',
                    'last_name': 'Иванов',
                    'city': 'Москва'
                },
                {
                    'email': 'student2@example.com',
                    'password': 'password123',
                    'first_name': 'Мария',
                    'last_name': 'Петрова',
                    'city': 'Санкт-Петербург'
                },
                {
                    'email': 'student3@example.com',
                    'password': 'password123',
                    'first_name': 'Алексей',
                    'last_name': 'Сидоров',
                    'city': 'Новосибирск'
                },
                {
                    'email': 'moderator@example.com',
                    'password': 'password123',
                    'first_name': 'Модератор',
                    'last_name': 'Модераторов',
                    'city': 'Москва'
                }
            ]

            for user_data in users_data:
                User.objects.create_user(**user_data)

            self.stdout.write(
                self.style.SUCCESS(f'Создано {len(users_data)} пользователей')
            )

        # Получаем пользователей для назначения владельцами
        users = list(User.objects.all())
        if not users:
            self.stdout.write(
                self.style.ERROR('Нет пользователей для создания курсов')
            )
            return

        # Создаем курсы, если их нет
        if not Course.objects.exists():
            courses_data = [
                {
                    'title': 'Python для начинающих',
                    'description': 'Изучение основ программирования на Python. Курс подходит для тех, кто только начинает свой путь в программировании.',
                    'owner': users[0]  # Первый пользователь
                },
                {
                    'title': 'Django Web Development',
                    'description': 'Создание веб-приложений с помощью Django. Изучение полного цикла разработки веб-приложений.',
                    'owner': users[1] if len(users) > 1 else users[0]  # Второй пользователь
                },
                {
                    'title': 'JavaScript Основы',
                    'description': 'Изучение JavaScript для фронтенд разработки. От основ до работы с DOM и событиями.',
                    'owner': users[2] if len(users) > 2 else users[0]  # Третий пользователь
                },
                {
                    'title': 'React для начинающих',
                    'description': 'Изучение библиотеки React для создания интерактивных пользовательских интерфейсов.',
                    'owner': users[0]  # Снова первый пользователь
                }
            ]

            courses = []
            for course_data in courses_data:
                course = Course.objects.create(**course_data)
                courses.append(course)

            self.stdout.write(
                self.style.SUCCESS(f'Создано {len(courses)} курсов')
            )

            # Создаем уроки для каждого курса
            lessons_data = {
                courses[0]: [  # Python для начинающих
                    {
                        'title': 'Введение в Python',
                        'description': 'Основы языка Python, установка и настройка среды разработки',
                        'video_url': 'https://www.youtube.com/watch?v=python_intro',
                        'owner': courses[0].owner
                    },
                    {
                        'title': 'Переменные и типы данных',
                        'description': 'Работа с переменными, числа, строки, списки, словари',
                        'video_url': 'https://www.youtube.com/watch?v=python_variables',
                        'owner': courses[0].owner
                    },
                    {
                        'title': 'Условия и циклы',
                        'description': 'Условные конструкции if/else, циклы for и while',
                        'video_url': 'https://www.youtube.com/watch?v=python_conditions',
                        'owner': courses[0].owner
                    },
                    {
                        'title': 'Функции',
                        'description': 'Создание и использование функций в Python',
                        'video_url': 'https://www.youtube.com/watch?v=python_functions',
                        'owner': courses[0].owner
                    }
                ],
                courses[1]: [  # Django Web Development
                    {
                        'title': 'Введение в Django',
                        'description': 'Основы фреймворка Django, создание проекта',
                        'video_url': 'https://www.youtube.com/watch?v=django_intro',
                        'owner': courses[1].owner
                    },
                    {
                        'title': 'Модели Django',
                        'description': 'Работа с базой данных, создание моделей',
                        'video_url': 'https://www.youtube.com/watch?v=django_models',
                        'owner': courses[1].owner
                    },
                    {
                        'title': 'Views и Templates',
                        'description': 'Создание представлений и шаблонов',
                        'video_url': 'https://www.youtube.com/watch?v=django_views',
                        'owner': courses[1].owner
                    }
                ],
                courses[2]: [  # JavaScript Основы
                    {
                        'title': 'Основы JavaScript',
                        'description': 'Введение в JavaScript, переменные, функции',
                        'video_url': 'https://www.youtube.com/watch?v=js_basics',
                        'owner': courses[2].owner
                    },
                    {
                        'title': 'DOM и события',
                        'description': 'Работа с DOM, обработка событий',
                        'video_url': 'https://www.youtube.com/watch?v=js_dom',
                        'owner': courses[2].owner
                    }
                ],
                courses[3]: [  # React для начинающих
                    {
                        'title': 'Введение в React',
                        'description': 'Основы React, создание компонентов',
                        'video_url': 'https://www.youtube.com/watch?v=react_intro',
                        'owner': courses[3].owner
                    },
                    {
                        'title': 'State и Props',
                        'description': 'Управление состоянием в React',
                        'video_url': 'https://www.youtube.com/watch?v=react_state',
                        'owner': courses[3].owner
                    }
                ]
            }

            total_lessons = 0
            for course, lessons in lessons_data.items():
                for lesson_data in lessons:
                    Lesson.objects.create(course=course, **lesson_data)
                    total_lessons += 1

            self.stdout.write(
                self.style.SUCCESS(f'Создано {total_lessons} уроков')
            )

        # Выводим статистику
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(f'Пользователей в базе: {User.objects.count()}')
        self.stdout.write(f'Курсов в базе: {Course.objects.count()}')
        self.stdout.write(f'Уроков в базе: {Lesson.objects.count()}')
        self.stdout.write('=' * 50)

        self.stdout.write(
            self.style.SUCCESS('\nТестовые данные успешно созданы!')
        )
        self.stdout.write('Следующие шаги:')
        self.stdout.write('1. python manage.py create_groups - создать группу модераторов')
        self.stdout.write('2. python manage.py load_payments --count 20 - загрузить платежи')
        self.stdout.write('3. Через админку добавить пользователей в группу модераторов')