from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import Group
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from decimal import Decimal
from .models import User, Payment
from lms.models import Course, Lesson, Subscription


class UserRegistrationTestCase(APITestCase):
    """Тесты для регистрации пользователей"""

    def setUp(self):
        self.register_url = reverse('user-register')

    def test_user_registration_success(self):
        """Тест успешной регистрации"""
        data = {
            'email': 'test@example.com',
            'password': 'strongpassword123',
            'password_confirm': 'strongpassword123',
            'first_name': 'Test',
            'last_name': 'User',
            'phone': '+7900123456',
            'city': 'Moscow'
        }

        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertTrue(User.objects.filter(email='test@example.com').exists())

    def test_user_registration_password_mismatch(self):
        """Тест регистрации с несовпадающими паролями"""
        data = {
            'email': 'test@example.com',
            'password': 'strongpassword123',
            'password_confirm': 'differentpassword',
            'first_name': 'Test'
        }

        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_registration_duplicate_email(self):
        """Тест регистрации с существующим email"""
        User.objects.create_user(email='test@example.com', password='password')

        data = {
            'email': 'test@example.com',
            'password': 'strongpassword123',
            'password_confirm': 'strongpassword123',
            'first_name': 'Test'
        }

        response = self.client.post(self.register_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class UserAuthenticationTestCase(APITestCase):
    """Тесты для аутентификации"""

    def setUp(self):
        self.login_url = reverse('token-obtain-pair')
        self.refresh_url = reverse('token-refresh')

        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpassword',
            first_name='Test'
        )

    def test_login_success(self):
        """Тест успешного входа"""
        data = {
            'email': 'test@example.com',
            'password': 'testpassword'
        }

        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)

    def test_login_invalid_credentials(self):
        """Тест входа с неверными данными"""
        data = {
            'email': 'test@example.com',
            'password': 'wrongpassword'
        }

        response = self.client.post(self.login_url, data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh(self):
        """Тест обновления токена"""
        refresh = RefreshToken.for_user(self.user)

        data = {'refresh': str(refresh)}
        response = self.client.post(self.refresh_url, data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)


class UserViewSetTestCase(APITestCase):
    """Тесты для ViewSet пользователей"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            email='user1@test.com',
            password='password',
            first_name='User1',
            last_name='LastName1',
            phone='+7900111111'
        )

        self.user2 = User.objects.create_user(
            email='user2@test.com',
            password='password',
            first_name='User2',
            phone='+7900222222'
        )

        self.users_url = reverse('user-list')
        self.user_me_url = reverse('user-me')

    def test_users_list_authenticated(self):
        """Тест получения списка пользователей"""
        self.client.force_authenticate(user=self.user1)

        response = self.client.get(self.users_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)  # Проверяем пагинацию

    def test_users_list_unauthenticated(self):
        """Тест получения списка без аутентификации"""
        response = self.client.get(self.users_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_me_endpoint(self):
        """Тест получения своего профиля"""
        self.client.force_authenticate(user=self.user1)

        response = self.client.get(self.user_me_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user1.email)
        self.assertIn('last_name', response.data)  # Приватная информация

    def test_user_detail_own_profile(self):
        """Тест получения детальной информации о своем профиле"""
        self.client.force_authenticate(user=self.user1)

        url = reverse('user-detail', kwargs={'pk': self.user1.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('last_name', response.data)  # Приватная информация
        self.assertIn('payments', response.data)

    def test_user_detail_other_profile(self):
        """Тест получения информации о чужом профиле"""
        self.client.force_authenticate(user=self.user1)

        url = reverse('user-detail', kwargs={'pk': self.user2.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertNotIn('last_name', response.data)  # Приватная информация скрыта
        self.assertNotIn('payments', response.data)

    def test_user_update_own_profile(self):
        """Тест обновления своего профиля"""
        self.client.force_authenticate(user=self.user1)

        url = reverse('user-detail', kwargs={'pk': self.user1.pk})
        data = {
            'first_name': 'Updated',
            'city': 'New City'
        }

        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user1.refresh_from_db()
        self.assertEqual(self.user1.first_name, 'Updated')

    def test_user_update_other_profile_forbidden(self):
        """Тест запрета обновления чужого профиля"""
        self.client.force_authenticate(user=self.user1)

        url = reverse('user-detail', kwargs={'pk': self.user2.pk})
        data = {'first_name': 'Hacked'}

        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_search(self):
        """Тест поиска пользователей"""
        self.client.force_authenticate(user=self.user1)

        response = self.client.get(self.users_url, {'search': 'User2'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем что найден правильный пользователь
        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['email'], 'user2@test.com')


class PaymentViewSetTestCase(APITestCase):
    """Тесты для ViewSet платежей"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            email='user1@test.com',
            password='password'
        )

        self.user2 = User.objects.create_user(
            email='user2@test.com',
            password='password'
        )

        self.moderator = User.objects.create_user(
            email='moderator@test.com',
            password='password'
        )
        moderators_group = Group.objects.get_or_create(name='Moderators')[0]
        self.moderator.groups.add(moderators_group)

        self.course = Course.objects.create(
            title='Test Course',
            description='Description',
            owner=self.user1
        )

        self.payment1 = Payment.objects.create(
            user=self.user1,
            course=self.course,
            amount=Decimal('1000.00'),
            payment_method='cash'
        )

        self.payment2 = Payment.objects.create(
            user=self.user2,
            course=self.course,
            amount=Decimal('2000.00'),
            payment_method='transfer'
        )

        self.payments_url = reverse('payment-list')

    def test_payments_list_user_sees_own(self):
        """Тест что пользователь видит только свои платежи"""
        self.client.force_authenticate(user=self.user1)

        response = self.client.get(self.payments_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.payment1.id)

    def test_payments_list_moderator_sees_all(self):
        """Тест что модератор видит все платежи"""
        self.client.force_authenticate(user=self.moderator)

        response = self.client.get(self.payments_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']
        self.assertEqual(len(results), 2)

    def test_payment_create(self):
        """Тест создания платежа"""
        self.client.force_authenticate(user=self.user1)

        data = {
            'course': self.course.id,
            'amount': '500.00',
            'payment_method': 'cash'
        }

        response = self.client.post(self.payments_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Проверяем что платеж создан для текущего пользователя
        payment = Payment.objects.get(id=response.data['id'])
        self.assertEqual(payment.user, self.user1)

    def test_payment_filter_by_course(self):
        """Тест фильтрации платежей по курсу"""
        self.client.force_authenticate(user=self.moderator)

        response = self.client.get(self.payments_url, {'course': self.course.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_payment_filter_by_method(self):
        """Тест фильтрации платежей по способу оплаты"""
        self.client.force_authenticate(user=self.moderator)

        response = self.client.get(self.payments_url, {'payment_method': 'cash'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_user_payments_endpoint(self):
        """Тест endpoint платежей пользователя"""
        self.client.force_authenticate(user=self.user1)

        url = reverse('user-payments', kwargs={'pk': self.user1.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)  # Пагинация

    def test_user_payments_other_user_forbidden(self):
        """Тест запрета доступа к платежам другого пользователя"""
        self.client.force_authenticate(user=self.user1)

        url = reverse('user-payments', kwargs={'pk': self.user2.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class CourseViewSetTestCase(APITestCase):
    """Тесты для ViewSet курсов"""

    def setUp(self):
        self.user1 = User.objects.create_user(
            email='user1@test.com',
            password='password'
        )

        self.user2 = User.objects.create_user(
            email='user2@test.com',
            password='password'
        )

        self.moderator = User.objects.create_user(
            email='moderator@test.com',
            password='password'
        )
        moderators_group = Group.objects.get_or_create(name='Moderators')[0]
        self.moderator.groups.add(moderators_group)

        self.course1 = Course.objects.create(
            title='Course 1',
            description='Description 1',
            owner=self.user1
        )

        self.course2 = Course.objects.create(
            title='Course 2',
            description='Description 2',
            owner=self.user2
        )

        self.courses_url = reverse('course-list')

    def test_courses_list_user_sees_own(self):
        """Тест что пользователь видит только свои курсы"""
        self.client.force_authenticate(user=self.user1)

        response = self.client.get(self.courses_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.course1.id)

    def test_courses_list_moderator_sees_all(self):
        """Тест что модератор видит все курсы"""
        self.client.force_authenticate(user=self.moderator)

        response = self.client.get(self.courses_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']
        self.assertEqual(len(results), 2)

    def test_course_create(self):
        """Тест создания курса"""
        self.client.force_authenticate(user=self.user1)

        data = {
            'title': 'New Course',
            'description': 'New Description'
        }

        response = self.client.post(self.courses_url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        course = Course.objects.get(id=response.data['id'])
        self.assertEqual(course.owner, self.user1)

    def test_course_create_by_moderator_forbidden(self):
        """Тест что модератор не может создавать курсы"""
        self.client.force_authenticate(user=self.moderator)

        data = {
            'title': 'New Course',
            'description': 'New Description'
        }

        response = self.client.post(self.courses_url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_course_detail_with_subscription_status(self):
        """Тест детального просмотра курса со статусом подписки"""
        # Создаем подписку
        Subscription.objects.create(user=self.user1, course=self.course1)

        self.client.force_authenticate(user=self.user1)

        url = reverse('course-detail', kwargs={'pk': self.course1.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_subscribed'])

    def test_course_lessons_endpoint(self):
        """Тест endpoint уроков курса"""
        lesson = Lesson.objects.create(
            title='Test Lesson',
            description='Description',
            video_url='https://youtube.com/watch?v=test',
            course=self.course1,
            owner=self.user1
        )

        self.client.force_authenticate(user=self.user1)

        url = reverse('course-lessons', kwargs={'pk': self.course1.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], lesson.id)

    def test_course_search(self):
        """Тест поиска курсов"""
        self.client.force_authenticate(user=self.user1)

        response = self.client.get(self.courses_url, {'search': 'Course 1'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        results = response.data['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['title'], 'Course 1')


class PaginationTestCase(APITestCase):
    """Тесты для пагинации"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@test.com',
            password='password'
        )

        # Создаем много курсов для тестирования пагинации
        for i in range(25):
            Course.objects.create(
                title=f'Course {i}',
                description=f'Description {i}',
                owner=self.user
            )

        self.courses_url = reverse('course-list')

    def test_courses_pagination(self):
        """Тест пагинации курсов"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.courses_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем структуру ответа с пагинацией
        self.assertIn('results', response.data)
        self.assertIn('pagination', response.data)
        self.assertIn('links', response.data)

        # По умолчанию должно быть 10 элементов на странице
        self.assertEqual(len(response.data['results']), 10)
        self.assertEqual(response.data['pagination']['count'], 25)
        self.assertEqual(response.data['pagination']['total_pages'], 3)

    def test_custom_page_size(self):
        """Тест кастомного размера страницы"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(self.courses_url, {'page_size': 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.assertEqual(len(response.data['results']), 5)
        self.assertEqual(response.data['pagination']['page_size'], 5)

    def test_page_navigation(self):
        """Тест навигации по страницам"""
        self.client.force_authenticate(user=self.user)

        # Первая страница
        response = self.client.get(self.courses_url, {'page': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['pagination']['has_next'])
        self.assertFalse(response.data['pagination']['has_previous'])

        # Вторая страница
        response = self.client.get(self.courses_url, {'page': 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['pagination']['has_next'])
        self.assertTrue(response.data['pagination']['has_previous'])


class APIEndpointsTestCase(APITestCase):
    """Тесты доступности всех API endpoints"""

    def setUp(self):
        self.user = User.objects.create_user(
            email='test@test.com',
            password='password'
        )

    def test_api_root(self):
        """Тест корневого endpoint API"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('message', response.data)
        self.assertIn('endpoints', response.data)

    def test_all_endpoints_require_authentication(self):
        """Тест что все основные endpoints требуют аутентификации"""
        protected_endpoints = [
            reverse('course-list'),
            reverse('lesson-list-create'),
            reverse('user-list'),
            reverse('payment-list'),
            reverse('subscription-toggle'),
        ]

        for endpoint in protected_endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f'Endpoint {endpoint} should require authentication'
            )

    def test_open_endpoints(self):
        """Тест открытых endpoints"""
        open_endpoints = [
            reverse('user-register'),
            reverse('token-obtain-pair'),
        ]

        for endpoint in open_endpoints:
            response = self.client.post(endpoint, {})
            # Не должно быть 401 (хотя может быть 400 из-за пустых данных)
            self.assertNotEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f'Endpoint {endpoint} should not require authentication'
            )