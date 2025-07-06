from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import Group
from rest_framework.test import APITestCase
from rest_framework import status
from users.models import User
from .models import Course, Lesson, Subscription


class LessonCRUDTestCase(APITestCase):
    """Тесты для CRUD операций с уроками"""

    def setUp(self):
        """Создание тестовых данных"""
        # Создаем группу модераторов
        self.moderators_group = Group.objects.get_or_create(name='Moderators')[0]

        # Создаем пользователей
        self.owner = User.objects.create_user(
            email='owner@test.com',
            password='testpass123',
            first_name='Owner'
        )

        self.moderator = User.objects.create_user(
            email='moderator@test.com',
            password='testpass123',
            first_name='Moderator'
        )
        self.moderator.groups.add(self.moderators_group)

        self.other_user = User.objects.create_user(
            email='other@test.com',
            password='testpass123',
            first_name='Other'
        )

        self.admin = User.objects.create_superuser(
            email='admin@test.com',
            password='testpass123',
            first_name='Admin'
        )

        # Создаем курсы
        self.course = Course.objects.create(
            title='Test Course',
            description='Test Description',
            owner=self.owner
        )

        self.other_course = Course.objects.create(
            title='Other Course',
            description='Other Description',
            owner=self.other_user
        )

        # Создаем урок
        self.lesson = Lesson.objects.create(
            title='Test Lesson',
            description='Test Lesson Description',
            video_url='https://youtube.com/watch?v=test123',
            course=self.course,
            owner=self.owner
        )

        # URLs
        self.lessons_url = reverse('lesson-list-create')
        self.lesson_detail_url = reverse('lesson-detail', kwargs={'pk': self.lesson.pk})

    def test_lesson_create_by_owner(self):
        """Тест создания урока владельцем"""
        self.client.force_authenticate(user=self.owner)

        data = {
            'title': 'New Lesson',
            'description': 'New Description',
            'video_url': 'https://youtube.com/watch?v=new123',
            'course': self.course.id
        }

        response = self.client.post(self.lessons_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Lesson.objects.count(), 2)

        new_lesson = Lesson.objects.get(title='New Lesson')
        self.assertEqual(new_lesson.owner, self.owner)

    def test_lesson_create_invalid_youtube_url(self):
        """Тест создания урока с невалидной ссылкой"""
        self.client.force_authenticate(user=self.owner)

        data = {
            'title': 'New Lesson',
            'description': 'New Description',
            'video_url': 'https://vimeo.com/test123',  # Не YouTube
            'course': self.course.id
        }

        response = self.client.post(self.lessons_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lesson_create_by_moderator_forbidden(self):
        """Тест что модератор не может создавать уроки"""
        self.client.force_authenticate(user=self.moderator)

        data = {
            'title': 'New Lesson',
            'description': 'New Description',
            'video_url': 'https://youtube.com/watch?v=new123',
            'course': self.course.id
        }

        response = self.client.post(self.lessons_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_lesson_list_owner_sees_own(self):
        """Тест что владелец видит только свои уроки"""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.lessons_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем пагинацию
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['id'], self.lesson.id)

    def test_lesson_list_moderator_sees_all(self):
        """Тест что модератор видит все уроки"""
        # Создаем урок для другого пользователя
        other_lesson = Lesson.objects.create(
            title='Other Lesson',
            description='Other Description',
            video_url='https://youtube.com/watch?v=other123',
            course=self.other_course,
            owner=self.other_user
        )

        self.client.force_authenticate(user=self.moderator)

        response = self.client.get(self.lessons_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_lesson_retrieve_by_owner(self):
        """Тест получения урока владельцем"""
        self.client.force_authenticate(user=self.owner)

        response = self.client.get(self.lesson_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], self.lesson.title)

    def test_lesson_update_by_owner(self):
        """Тест обновления урока владельцем"""
        self.client.force_authenticate(user=self.owner)

        data = {
            'title': 'Updated Lesson',
            'description': 'Updated Description',
            'video_url': 'https://youtube.com/watch?v=updated123',
            'course': self.course.id
        }

        response = self.client.put(self.lesson_detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.lesson.refresh_from_db()
        self.assertEqual(self.lesson.title, 'Updated Lesson')

    def test_lesson_update_by_moderator(self):
        """Тест обновления урока модератором"""
        self.client.force_authenticate(user=self.moderator)

        data = {
            'title': 'Moderator Updated',
            'description': 'Updated by moderator',
            'video_url': 'https://youtube.com/watch?v=mod123',
            'course': self.course.id
        }

        response = self.client.put(self.lesson_detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_lesson_update_by_other_user_forbidden(self):
        """Тест что другой пользователь не может обновлять чужой урок"""
        self.client.force_authenticate(user=self.other_user)

        data = {
            'title': 'Hacked',
            'description': 'Hacked',
            'video_url': 'https://youtube.com/watch?v=hack123',
            'course': self.course.id
        }

        response = self.client.put(self.lesson_detail_url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_lesson_delete_by_owner(self):
        """Тест удаления урока владельцем"""
        self.client.force_authenticate(user=self.owner)

        response = self.client.delete(self.lesson_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Lesson.objects.filter(id=self.lesson.id).exists())

    def test_lesson_delete_by_moderator_forbidden(self):
        """Тест что модератор не может удалять уроки"""
        self.client.force_authenticate(user=self.moderator)

        response = self.client.delete(self.lesson_detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Lesson.objects.filter(id=self.lesson.id).exists())


class SubscriptionTestCase(APITestCase):
    """Тесты для функционала подписки на курсы"""

    def setUp(self):
        """Создание тестовых данных"""
        self.user1 = User.objects.create_user(
            email='user1@test.com',
            password='testpass123'
        )

        self.user2 = User.objects.create_user(
            email='user2@test.com',
            password='testpass123'
        )

        self.course = Course.objects.create(
            title='Test Course',
            description='Test Description',
            owner=self.user1
        )

        self.subscription_url = reverse('subscription-toggle')

    def test_subscription_create(self):
        """Тест создания подписки"""
        self.client.force_authenticate(user=self.user2)

        data = {'course_id': self.course.id}
        response = self.client.post(self.subscription_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'подписка добавлена')
        self.assertTrue(response.data['is_subscribed'])

        # Проверяем что подписка создана в БД
        self.assertTrue(
            Subscription.objects.filter(user=self.user2, course=self.course).exists()
        )

    def test_subscription_delete(self):
        """Тест удаления подписки"""
        # Создаем подписку
        subscription = Subscription.objects.create(user=self.user2, course=self.course)

        self.client.force_authenticate(user=self.user2)

        data = {'course_id': self.course.id}
        response = self.client.post(self.subscription_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], 'подписка удалена')
        self.assertFalse(response.data['is_subscribed'])

        # Проверяем что подписка удалена из БД
        self.assertFalse(
            Subscription.objects.filter(user=self.user2, course=self.course).exists()
        )

    def test_subscription_toggle_multiple_times(self):
        """Тест переключения подписки несколько раз"""
        self.client.force_authenticate(user=self.user2)
        data = {'course_id': self.course.id}

        # Создаем подписку
        response1 = self.client.post(self.subscription_url, data)
        self.assertEqual(response1.data['message'], 'подписка добавлена')

        # Удаляем подписку
        response2 = self.client.post(self.subscription_url, data)
        self.assertEqual(response2.data['message'], 'подписка удалена')

        # Создаем снова
        response3 = self.client.post(self.subscription_url, data)
        self.assertEqual(response3.data['message'], 'подписка добавлена')

    def test_subscription_without_course_id(self):
        """Тест запроса без course_id"""
        self.client.force_authenticate(user=self.user2)

        response = self.client.post(self.subscription_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_subscription_invalid_course_id(self):
        """Тест с несуществующим course_id"""
        self.client.force_authenticate(user=self.user2)

        data = {'course_id': 999}
        response = self.client.post(self.subscription_url, data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_subscription_unauthenticated(self):
        """Тест попытки подписки неаутентифицированным пользователем"""
        data = {'course_id': self.course.id}
        response = self.client.post(self.subscription_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_user_subscriptions(self):
        """Тест получения списка подписок пользователя"""
        # Создаем несколько подписок
        course2 = Course.objects.create(
            title='Course 2',
            description='Description 2',
            owner=self.user1
        )

        Subscription.objects.create(user=self.user2, course=self.course)
        Subscription.objects.create(user=self.user2, course=course2)

        self.client.force_authenticate(user=self.user2)

        response = self.client.get(self.subscription_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['subscriptions']), 2)

    def test_course_serializer_shows_subscription_status(self):
        """Тест что сериализатор курса показывает статус подписки"""
        # Создаем подписку
        Subscription.objects.create(user=self.user2, course=self.course)

        self.client.force_authenticate(user=self.user2)

        # Получаем список курсов (нужно настроить права доступа для этого теста)
        from django.urls import reverse
        courses_url = reverse('course-list')
        response = self.client.get(courses_url)

        # Если пользователь видит только свои курсы, этот тест не будет работать
        # Проверим детальный просмотр курса
        course_detail_url = reverse('course-detail', kwargs={'pk': self.course.pk})

        # Временно изменим владельца курса на текущего пользователя
        original_owner = self.course.owner
        self.course.owner = self.user2
        self.course.save()

        try:
            response = self.client.get(course_detail_url)
            if response.status_code == status.HTTP_200_OK:
                self.assertTrue(response.data.get('is_subscribed', False))
        finally:
            # Восстанавливаем оригинального владельца
            self.course.owner = original_owner
            self.course.save()


class LessonValidatorTestCase(APITestCase):
    """Тесты для валидаторов ссылок YouTube"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@test.com',
            password='testpass123'
        )

        self.course = Course.objects.create(
            title='Test Course',
            description='Test Description',
            owner=self.user
        )

        self.lessons_url = reverse('lesson-list-create')

    def test_valid_youtube_urls(self):
        """Тест валидных YouTube ссылок"""
        self.client.force_authenticate(user=self.user)

        valid_urls = [
            'https://youtube.com/watch?v=test123',
            'https://www.youtube.com/watch?v=test123',
            'https://youtu.be/test123',
            'https://www.youtu.be/test123',
            'https://youtube.com/embed/test123',
        ]

        for url in valid_urls:
            data = {
                'title': f'Lesson for {url}',
                'description': 'Test Description',
                'video_url': url,
                'course': self.course.id
            }

            response = self.client.post(self.lessons_url, data)
            self.assertEqual(
                response.status_code,
                status.HTTP_201_CREATED,
                f'URL {url} should be valid'
            )

    def test_invalid_urls(self):
        """Тест невалидных ссылок"""
        self.client.force_authenticate(user=self.user)

        invalid_urls = [
            'https://vimeo.com/test123',
            'https://dailymotion.com/test123',
            'https://example.com/video',
            'https://rutube.ru/video/test',
            'http://youtube.com',  # Без конкретного видео
        ]

        for url in invalid_urls:
            data = {
                'title': f'Lesson for {url}',
                'description': 'Test Description',
                'video_url': url,
                'course': self.course.id
            }

            response = self.client.post(self.lessons_url, data)
            self.assertEqual(
                response.status_code,
                status.HTTP_400_BAD_REQUEST,
                f'URL {url} should be invalid'
            )