from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.shortcuts import reverse
from django.test import Client, TestCase

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.post = Post.objects.create(
            text='Привет, как дела?',
            author=cls.user,
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='HasNoName')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_post_create_and_edit(self):
        context = {
            reverse('posts:post_create'): HTTPStatus.OK,
            reverse('posts:post_edit',
                    args={PostURLTests.post.id}): HTTPStatus.OK
        }
        for url, status_code in context.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url).status_code
                self.assertEqual(response, status_code)

    def test_urls_guest_client(self):
        """Проверка доступа для неавторизованного пользователя."""
        status_code_for_urls = {
            reverse('posts:main_page'): HTTPStatus.OK,
            reverse('posts:posts_list',
                    args={PostURLTests.group.slug}): HTTPStatus.OK,
            reverse('posts:profile',
                    args={PostURLTests.post.author}): HTTPStatus.OK,
            reverse('posts:post_create'): HTTPStatus.FOUND,
            reverse('posts:post_detail',
                    args={PostURLTests.post.id}): HTTPStatus.OK,
            reverse('posts:post_edit',
                    args={PostURLTests.post.id}): HTTPStatus.FOUND,
            '/unexisting_page/': HTTPStatus.NOT_FOUND,
            reverse('about:author'): HTTPStatus.OK,
            reverse('about:tech'): HTTPStatus.OK,
        }
        for url, status_code in status_code_for_urls.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url).status_code
                self.assertEqual(response, status_code)

    def test_templates(self):
        """Проверка доступа к шаблонам."""
        context_of_templates = {
            reverse('posts:main_page'): 'posts/index.html',
            reverse('posts:posts_list',
                    args={PostURLTests.group.slug}): 'posts/group_list.html',
            reverse('posts:profile',
                    args={PostURLTests.post.author}): 'posts/profile.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_detail',
                    args={PostURLTests.post.id}): 'posts/post_detail.html',
            reverse('posts:post_edit',
                    args={PostURLTests.post.id}): 'posts/create_post.html',
            reverse('about:author'): 'about/author.html',
            reverse('about:tech'): 'about/tech.html',
        }
        for adress, template in context_of_templates.items():
            with self.subTest(adress=adress):
                response = self.authorized_client.get(adress)
                self.assertTemplateUsed(response, template)
