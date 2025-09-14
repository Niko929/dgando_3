from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from .models import Course, Lesson, Subscription

User = get_user_model()


class LessonCRUDTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

        # Создаем пользователей
        self.user1 = User.objects.create_user(
            email='user1@test.com',
            password='testpass123',
            is_active=True
        )

        self.user2 = User.objects.create_user(
            email='user2@test.com',
            password='testpass123',
            is_active=True
        )

        # Создаем курс
        self.course = Course.objects.create(
            title='Test Course',
            description='Test Description',
            owner=self.user1
        )

        # Создаем уроки
        self.lesson1 = Lesson.objects.create(
            title='Test Lesson 1',
            description='Test Description 1',
            video_url='https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            course=self.course,
            owner=self.user1
        )

        self.lesson2 = Lesson.objects.create(
            title='Test Lesson 2',
            description='Test Description 2',
            video_url='https://youtu.be/dQw4w9WgXcQ',
            course=self.course,
            owner=self.user1
        )

    def test_create_lesson_with_valid_youtube_link(self):
        """Тест создания урока с валидной YouTube ссылкой"""
        self.client.force_authenticate(user=self.user1)

        data = {
            'title': 'New Lesson',
            'description': 'New Description',
            'video_url': 'https://www.youtube.com/watch?v=test123',
            'course': self.course.id
        }

        response = self.client.post(reverse('lesson-list'), data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Lesson.objects.count(), 3)

    def test_create_lesson_with_invalid_link(self):
        """Тест создания урока с невалидной ссылкой"""
        self.client.force_authenticate(user=self.user1)

        data = {
            'title': 'New Lesson',
            'description': 'New Description',
            'video_url': 'https://vk.com/video123',
            'course': self.course.id
        }

        response = self.client.post(reverse('lesson-list'), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Разрешены только ссылки на YouTube', str(response.data))

    def test_update_lesson_with_valid_link(self):
        """Тест обновления урока с валидной ссылкой"""
        self.client.force_authenticate(user=self.user1)

        data = {
            'title': 'Updated Lesson',
            'video_url': 'https://youtu.be/newvideo123'
        }

        response = self.client.patch(
            reverse('lesson-detail', args=[self.lesson1.id]),
            data
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.lesson1.refresh_from_db()
        self.assertEqual(self.lesson1.video_url, 'https://youtu.be/newvideo123')

    def test_user_cannot_access_others_lessons(self):
        """Тест, что пользователь не может получить доступ к чужим урокам"""
        self.client.force_authenticate(user=self.user2)

        response = self.client.get(reverse('lesson-detail', args=[self.lesson1.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_list_lessons_pagination(self):
        """Тест пагинации списка уроков"""
        self.client.force_authenticate(user=self.user1)

        # Создаем дополнительные уроки для тестирования пагинации
        for i in range(15):
            Lesson.objects.create(
                title=f'Lesson {i + 3}',
                description=f'Description {i + 3}',
                video_url=f'https://www.youtube.com/watch?v=test{i}',
                course=self.course,
                owner=self.user1
            )

        response = self.client.get(reverse('lesson-list') + '?page=2')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 10)


class SubscriptionTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

        self.user1 = User.objects.create_user(
            email='user1@test.com',
            password='testpass123',
            is_active=True
        )

        self.user2 = User.objects.create_user(
            email='user2@test.com',
            password='testpass123',
            is_active=True
        )

        self.course = Course.objects.create(
            title='Test Course',
            description='Test Description',
            owner=self.user1
        )

    def test_subscribe_to_course(self):
        """Тест подписки на курс"""
        self.client.force_authenticate(user=self.user1)

        response = self.client.post(
            reverse('course-subscribe', args=[self.course.id])
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Subscription.objects.count(), 1)
        self.assertTrue(Subscription.objects.filter(
            user=self.user1,
            course=self.course,
            is_active=True
        ).exists())

    def test_unsubscribe_from_course(self):
        """Тест отписки от курса"""
        # Сначала подписываемся
        subscription = Subscription.objects.create(
            user=self.user1,
            course=self.course,
            is_active=True
        )

        self.client.force_authenticate(user=self.user1)

        response = self.client.delete(
            reverse('course-subscribe', args=[self.course.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        subscription.refresh_from_db()
        self.assertFalse(subscription.is_active)

    def test_subscription_status_in_course_response(self):
        """Тест отображения статуса подписки в ответе курса"""
        # Создаем подписку
        Subscription.objects.create(
            user=self.user1,
            course=self.course,
            is_active=True
        )

        self.client.force_authenticate(user=self.user1)

        response = self.client.get(reverse('course-detail', args=[self.course.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_subscribed'])

    def test_cannot_subscribe_twice(self):
        """Тест, что нельзя подписаться дважды"""
        self.client.force_authenticate(user=self.user1)

        # Первая подписка
        response1 = self.client.post(
            reverse('course-subscribe', args=[self.course.id])
        )
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Вторая попытка подписки
        response2 = self.client.post(
            reverse('course-subscribe', args=[self.course.id])
        )
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)  # Должно обновить существующую

        # Должна быть только одна активная подписка
        active_subscriptions = Subscription.objects.filter(
            user=self.user1,
            course=self.course,
            is_active=True
        )
        self.assertEqual(active_subscriptions.count(), 1)


class CoursePaginationTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()

        self.user = User.objects.create_user(
            email='user@test.com',
            password='testpass123',
            is_active=True
        )

        # Создаем несколько курсов для тестирования пагинации
        for i in range(8):
            Course.objects.create(
                title=f'Course {i + 1}',
                description=f'Description {i + 1}',
                owner=self.user
            )

    def test_course_pagination(self):
        """Тест пагинации курсов"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('course-list') + '?page=2')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 3)  # 8 курсов, page_size=5, на второй странице 3

    def test_course_page_size_parameter(self):
        """Тест параметра page_size"""
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('course-list') + '?page_size=3&page=2')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 3)
