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
                }
            ]

            for user_data in users_data:
                User.objects.create_user(**user_data)

            self.stdout.write(
                self.style.SUCCESS(f'Создано {len(users_data)} пользователей')
            )

        # Создаем курсы, если их нет
        if not Course.objects.exists():
            courses_data = [
                {
                    'title': 'Python для начинающих',
                    'description': 'Изучение основ программирования на Python. Курс подходит для тех, кто только начинает свой путь в программировании.'
                },
                {
                    'title': 'Django Web Development',
                    'description': 'Создание веб-приложений с помощью Django. Изучение полного цикла разработки веб-приложений.'
                },
                {
                    'title': 'JavaScript Основы',
                    'description': 'Изучение JavaScript для фронтенд разработки. От основ до работы с DOM и событиями.'
                },
                {
                    'title': 'React для начинающих',
                    'description': 'Изучение библиотеки React для создания интерактивных пользовательских интерфейсов.'
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
                        'video_url': 'https://www.youtube.com/watch?v=python_intro'
                    },
                    {
                        'title': 'Переменные и типы данных',
                        'description': 'Работа с переменными, числа, строки, списки, словари',
                        'video_url': 'https://www.youtube.com/watch?v=python_variables'
                    },
                    {
                        'title': 'Условия и циклы',
                        'description': 'Условные конструкции if/else, циклы for и while',
                        'video_url': 'https://www.youtube.com/watch?v=python_conditions'
                    },
                    {
                        'title': 'Функции',
                        'description': 'Создание и использование функций в Python',
                        'video_url': 'https://www.youtube.com/watch?v=python_functions'
                    }
                ],
                courses[1]: [  # Django Web Development
                    {
                        'title': 'Введение в Django',
                        'description': 'Основы фреймворка Django, создание проекта',
                        'video_url': 'https://www.youtube.com/watch?v=django_intro'
                    },
                    {
                        'title': 'Модели Django',
                        'description': 'Работа с базой данных, создание моделей',
                        'video_url': 'https://www.youtube.com/watch?v=django_models'
                    },
                    {
                        'title': 'Views и Templates',
                        'description': 'Создание представлений и шаблонов',
                        'video_url': 'https://www.youtube.com/watch?v=django_views'
                    }
                ],
                courses[2]: [  # JavaScript Основы
                    {
                        'title': 'Основы JavaScript',
                        'description': 'Введение в JavaScript, переменные, функции',
                        'video_url': 'https://www.youtube.com/watch?v=js_basics'
                    },
                    {
                        'title': 'DOM и события',
                        'description': 'Работа с DOM, обработка событий',
                        'video_url': 'https://www.youtube.com/watch?v=js_dom'
                    }
                ],
                courses[3]: [  # React для начинающих
                    {
                        'title': 'Введение в React',
                        'description': 'Основы React, создание компонентов',
                        'video_url': 'https://www.youtube.com/watch?v=react_intro'
                    },
                    {
                        'title': 'State и Props',
                        'description': 'Управление состоянием в React',
                        'video_url': 'https://www.youtube.com/watch?v=react_state'
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
        self.stdout.write('Теперь вы можете запустить: python manage.py load_payments --count 20')