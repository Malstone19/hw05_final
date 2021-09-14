import shutil
import tempfile

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
        cls.author_2 = User.objects.create_user(username='auth_2')
        cls.author_3 = User.objects.create_user(username='auth_3')
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.image = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.group_2 = Group.objects.create(
            title='Тестовая группаggg',
            slug='test-sluggg',
            description='Тестовое описаниеggg',
        )
        cls.post = Post.objects.create(
            text='Привет, как дела?',
            author=PostsViewsTests.author,
            group=PostsViewsTests.group,
            image=PostsViewsTests.image
        )
        cls.comment = Comment.objects.create(
            post=PostsViewsTests.post,
            author=PostsViewsTests.author,
            text='блабла'
        )
        cls.follow = Follow.objects.create(
            user=PostsViewsTests.author,
            author=PostsViewsTests.author_2
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
                    kwargs={'post_id': id}): 'posts/post_detail.html',
            reverse('posts:profile',
                    kwargs={'username': author_test}): 'posts/profile.html',
            reverse('posts:post_edit',
                    kwargs={'post_id': id}): 'posts/create_post.html',
            reverse('posts:post_create'): 'posts/create_post.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def try_to_be(self, first_object):
        post_text_0 = first_object.text
        post_author_0 = first_object.author
        post_group_0 = first_object.group
        post_image_0 = first_object.image
        self.assertEqual(post_image_0, f'posts/{PostsViewsTests.image}')
        self.assertEqual(post_text_0, PostsViewsTests.post.text)
        self.assertEqual(post_author_0, PostsViewsTests.author)
        self.assertEqual(post_group_0, PostsViewsTests.group)

    def test_index_context(self):
        response = self.authorized_client.get(reverse('posts:main_page'))
        first_object = response.context['page_obj'][0]
        self.try_to_be(first_object)

    def test_cache(self):
        posts_count = Post.objects.count()
        new_post = Post.objects.create(
            text='куку',
            author=PostsViewsTests.author,
            group=PostsViewsTests.group,
            image=PostsViewsTests.image
        )
        response_1 = self.authorized_client.get(reverse('posts:main_page'))
        self.assertEqual(Post.objects.count(), posts_count + 1)
        new_post.delete()
        response_2 = self.authorized_client.get(reverse('posts:main_page'))
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertEqual(response_1.content, response_2.content)
        cache.clear()
        response_3 = self.authorized_client.get(reverse('posts:main_page'))
        self.assertNotEqual(response_2.content, response_3.content)

    def test_following_yes(self):
        Post.objects.create(
            text='к',
            author=PostsViewsTests.author_2,
            group=PostsViewsTests.group_2,
            image=PostsViewsTests.image
        )
        response = self.authorized_client.get(reverse('posts:follow_index'))
        first_object = response.context['page_obj'][0]
        post_group_0 = first_object.group
        self.assertEqual(post_group_0, PostsViewsTests.group_2)

    def test_following_no(self):
        response_1 = self.authorized_client.get(reverse('posts:follow_index'))
        Post.objects.create(
            text='ку',
            author=PostsViewsTests.author_3,
            group=PostsViewsTests.group_2,
            image=PostsViewsTests.image
        )
        response_2 = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(response_1.content, response_2.content)

    def test_follow_index(self):
        response_1 = self.authorized_client.get(reverse('posts:follow_index'))
        new = Follow.objects.create(
            user=PostsViewsTests.author,
            author=PostsViewsTests.author_3
        )
        Post.objects.create(
            text='к',
            author=PostsViewsTests.author_3,
            group=PostsViewsTests.group_2,
            image=PostsViewsTests.image
        )
        new.delete()
        response_2 = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertEqual(response_1.content, response_2.content)

    def test_group_list_context(self):
        slug_test = PostsViewsTests.group.slug
        title_test = PostsViewsTests.group.title
        response = (self.authorized_client.get(reverse('posts:posts_list',
                    kwargs={'slug': slug_test})))
        first_object = response.context['page_obj'][0]
        self.try_to_be(first_object)
        self.assertEqual(response.context.get('group').title, title_test)
        self.assertEqual(response.context.get('group').slug, slug_test)

    def test_profile_context(self):
        author_test = PostsViewsTests.author
        posts_count = Post.objects.count()
        response = (self.authorized_client.get(reverse('posts:profile',
                    kwargs={'username': author_test})))
        first_object = response.context['page_obj'][0]
        self.try_to_be(first_object)
        self.assertEqual(response.context.get('post_amount'), posts_count)
        self.assertEqual(response.context.get('author'), author_test)

    def test_post_detail(self):
        id = PostsViewsTests.post.id
        text_test = PostsViewsTests.post.text
        author_test = PostsViewsTests.author
        comment_test = PostsViewsTests.comment
        response = (self.authorized_client.
                    get(reverse('posts:post_detail', kwargs={'post_id': id})))
        first_object = response.context['post']
        post_image_0 = first_object.image
        self.assertEqual(post_image_0, f'posts/{PostsViewsTests.image}')
        self.assertEqual(response.context.get('post').author, author_test)
        self.assertEqual(response.context.get('post').text, text_test)
        self.assertEqual(response.context.get('comments')[0], comment_test)

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
                form_field = response.context.get('form').fields.get(value)
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
                form_field = response.context.get('form').fields.get(value)
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

    def test_index_paginator_first_page(self):
        response = self.guest_client.get(reverse('posts:main_page'))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_index_paginator_next_page(self):
        response = (self.guest_client.get(reverse('posts:main_page')
                    + '?page=2'))
        self.assertEqual(len(response.context['page_obj']), 3)

    def test_group_list_paginator_first_page(self):
        slug_test = PaginatorViewsTest.group.slug
        response = self.guest_client.get(reverse('posts:posts_list',
                                                 kwargs={'slug': slug_test}))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_group_list_next_page(self):
        slug_test = PaginatorViewsTest.group.slug
        response = (self.guest_client.get(reverse('posts:posts_list',
                    kwargs={'slug': slug_test}) + '?page=2'))
        self.assertEqual(len(response.context['page_obj']), 3)

    def test_profile_paginator_first_page(self):
        slug_author = PaginatorViewsTest.post.author
        response = (self.authorized_client.get(reverse('posts:profile',
                    kwargs={'username': slug_author})))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_profile_paginator_next_page(self):
        slug_author = PaginatorViewsTest.post.author
        response = (self.authorized_client.get(reverse('posts:profile',
                    kwargs={'username': slug_author}) + '?page=2'))
        self.assertEqual(len(response.context['page_obj']), 3)
