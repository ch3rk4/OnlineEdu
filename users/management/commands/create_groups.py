from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from lms.models import Course, Lesson
from users.models import Payment


class Command(BaseCommand):
    help = 'Создает группы пользователей и назначает им права'

    def handle(self, *args, **options):
        # Создаем группу модераторов
        moderators_group, created = Group.objects.get_or_create(name='Moderators')

        if created:
            self.stdout.write(
                self.style.SUCCESS('Создана группа "Moderators"')
            )
        else:
            self.stdout.write('Группа "Moderators" уже существует')

        # Получаем типы контента
        course_content_type = ContentType.objects.get_for_model(Course)
        lesson_content_type = ContentType.objects.get_for_model(Lesson)
        payment_content_type = ContentType.objects.get_for_model(Payment)

        # Права для модераторов (только просмотр и изменение, без создания и удаления)
        moderator_permissions = [
            # Курсы
            Permission.objects.get(content_type=course_content_type, codename='view_course'),
            Permission.objects.get(content_type=course_content_type, codename='change_course'),

            # Уроки
            Permission.objects.get(content_type=lesson_content_type, codename='view_lesson'),
            Permission.objects.get(content_type=lesson_content_type, codename='change_lesson'),

            # Платежи (только просмотр)
            Permission.objects.get(content_type=payment_content_type, codename='view_payment'),
        ]

        # Назначаем права группе модераторов
        moderators_group.permissions.set(moderator_permissions)

        self.stdout.write(
            self.style.SUCCESS(
                f'Группе "Moderators" назначено {len(moderator_permissions)} прав'
            )
        )

        # Выводим информацию о созданных группах
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write('Созданные группы и их права:')
        self.stdout.write('=' * 50)

        for group in Group.objects.all():
            self.stdout.write(f'\nГруппа: {group.name}')
            permissions = group.permissions.all()
            if permissions:
                for perm in permissions:
                    self.stdout.write(f'  - {perm.name}')
            else:
                self.stdout.write('  - Нет специальных прав')

        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(
            self.style.SUCCESS('Группы успешно созданы и настроены!')
        )
        self.stdout.write('Теперь можно добавлять пользователей в группы через админку.')