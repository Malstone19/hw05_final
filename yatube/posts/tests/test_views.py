import shutil
import tempfile
from http import HTTPStatus

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Comment, Follow, Group, Post

User = get_user_model()


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsViewsTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='auth')
        cls.following_author = User.objects.create_user(username='auth_2')
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            text='Привет, как дела?',
            author=PostsViewsTests.author,
            group=PostsViewsTests.group,
            image=uploaded
        )
        cls.comment = Comment.objects.create(
            post=PostsViewsTests.post,
            author=PostsViewsTests.author,
            text='блабла'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PostsViewsTests.author)

    def test_urls(self):
        """Проверка namespace:name."""
        slug_test = PostsViewsTests.group.slug
        author_test = PostsViewsTests.author
        id = PostsViewsTests.post.id
        templates_pages_names = {
            reverse('posts:main_page'): 'posts/index.html',
            reverse('posts:posts_list',
                    kwargs={'slug': slug_test}): 'posts/group_list.html',
            reverse('posts:post_detail',
                    kwargs={'post_id': id}):
                        'posts/post_detail.html',
            reverse('posts:profile',
                    kwargs={'username': author_test}): 'posts/profile.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': id}):
                        'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def defaul_post_tests(self, first_test_post_object):
        post_text_0 = first_test_post_object.text
        post_author_0 = first_test_post_object.author
        post_group_0 = first_test_post_object.group
        post_image_0 = first_test_post_object.image
        self.assertEqual(post_image_0, self.post.image)
        self.assertEqual(post_text_0, self.post.text)
        self.assertEqual(post_author_0, self.post.author)
        self.assertEqual(post_group_0, self.post.group)

    def test_index_context(self):
        response = self.authorized_client.get(reverse('posts:main_page'))
        first_object = response.context['page_obj'][0]
        self.defaul_post_tests(first_object)

    def test_cache(self):
        new_post = Post.objects.create(
            text='куку',
            author=PostsViewsTests.author,
            group=PostsViewsTests.group,
        )
        response_1 = self.authorized_client.get(reverse('posts:main_page'))
        new_post.delete()
        response_2 = self.authorized_client.get(reverse('posts:main_page'))
        self.assertEqual(response_1.content, response_2.content)
        cache.clear()
        response_3 = self.authorized_client.get(reverse('posts:main_page'))
        self.assertNotEqual(response_2.content, response_3.content)

    def test_following_yes(self):
        follow_count_begin = Follow.objects.count()
        follow = Follow.objects.filter(user=PostsViewsTests.author,
                                       author=PostsViewsTests.following_author)
        self.assertEqual(follow.first(), None)
        response = (self.authorized_client.
                    get(reverse('posts:profile_follow',
                        kwargs={'username': PostsViewsTests.following_author.
                                username})))
        follow_count_after = Follow.objects.count()
        self.assertEqual(follow_count_after, follow_count_begin + 1)
        follow_first = Follow.objects.first()
        self.assertEqual(follow_first.user, PostsViewsTests.author)
        self.assertEqual(follow_first.author, PostsViewsTests.following_author)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_post_detail(self):
        id = PostsViewsTests.post.id
        comment_test = PostsViewsTests.comment
        response = (self.authorized_client.
                    get(reverse('posts:post_detail', kwargs={'post_id': id})))
        first_object = response.context['post']
        self.defaul_post_tests(first_object)
        self.assertEqual(response.context['comments'][0], comment_test)

    def test_follow_auth_index(self):
        Follow.objects.create(
            user=PostsViewsTests.author,
            author=PostsViewsTests.following_author
        )
        post = Post.objects.create(
            text='к',
            author=PostsViewsTests.following_author,
            group=PostsViewsTests.group,
        )
        response = (self.authorized_client.get(reverse('posts:follow_index')))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object, post)

    def test_follow_not_auth_index(self):
        not_followed_user = User.objects.create_user(username='user')
        self.not_followed_client = Client()
        self.not_followed_client.force_login(not_followed_user)
        Follow.objects.create(
            user=PostsViewsTests.author,
            author=PostsViewsTests.following_author
        )
        Post.objects.create(
            text='к',
            author=PostsViewsTests.following_author,
            group=PostsViewsTests.group,
        )
        response = self.not_followed_client.get(reverse('posts:follow_index'))
        self.assertEqual(len(response.context['page_obj']), 0)

    def test_post_correct_group(self):
        clear_group = Group.objects.create(
            title='Пустая группа',
            slug='test-clear',
            description='Описание тут',
        )
        response = (self.authorized_client.get(reverse('posts:posts_list',
                    kwargs={'slug': clear_group.slug})))
        self.assertEqual(len(response.context['page_obj']), 0)

    def test_group_list_context(self):
        slug_test = PostsViewsTests.group.slug
        title_test = PostsViewsTests.group.title
        response = (self.authorized_client.get(reverse('posts:posts_list',
                    kwargs={'slug': slug_test})))
        first_object = response.context['page_obj'][0]
        self.defaul_post_tests(first_object)
        self.assertEqual(response.context['group'].title, title_test)
        self.assertEqual(response.context['group'].slug, slug_test)

    def test_profile_context(self):
        author_test = PostsViewsTests.author
        response = (self.authorized_client.get(reverse('posts:profile',
                    kwargs={'username': author_test})))
        first_object = response.context['page_obj'][0]
        self.defaul_post_tests(first_object)
        self.assertEqual(response.context['author'], author_test)

    def test_post_edit(self):
        id = PostsViewsTests.post.id
        response = (self.authorized_client.
                    get(reverse('posts:post_edit',
                        kwargs={'post_id': id})))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_create(self):
        response = (self.authorized_client.
                    get(reverse('posts:post_create')))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields.get(value)
                self.assertIsInstance(form_field, expected)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='noauthor')
        cls.group = Group.objects.create(
            title='Тестовая',
            slug='test-slug')
        for i in range(13):
            cls.post = Post.objects.create(
                text='Привет, как дела?',
                author=PaginatorViewsTest.author,
                group=PaginatorViewsTest.group
            )

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(PaginatorViewsTest.author)

    def test_paginator(self):
        urls = [reverse('posts:main_page'),
                reverse('posts:posts_list',
                        kwargs={'slug':
                                PaginatorViewsTest.group.slug}),
                reverse('posts:profile',
                        kwargs={'username':
                                PaginatorViewsTest.post.author})]
        for url in urls:
            with self.subTest(url=url):
                response_10 = self.client.get(url)
                response_3 = self.client.get(url + '?page=2')
                self.assertEqual(len(
                    response_10.context['page_obj']), 10
                )
                self.assertEqual(len(
                    response_3.context['page_obj']), 3
                )
