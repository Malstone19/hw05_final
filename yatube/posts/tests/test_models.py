from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовая группа',
        )

    def test_models_have_correct_object_post(self):
        """Проверяем, что у моделей post корректно работает __str__."""
        post = PostModelTest.post
        expected_text = post.text[:15]
        self.assertEqual(expected_text, str(post))

    def test_models_have_correct_object_group(self):
        """Проверяем, что у модели group корректно работает __str__"""
        group = PostModelTest.group
        expected_title = group.title
        self.assertEqual(expected_title, str(group))
