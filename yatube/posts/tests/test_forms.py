import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Comment, Group, Post

User = get_user_model()


TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TaskCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая',
            slug='test')
        cls.post = Post.objects.create(
            text='Привет, как дела?',
            author=TaskCreateFormTests.user,
            group=TaskCreateFormTests.group
        )
        cls.form = PostForm()
        Post.objects.create(
            text='Привет, как дела?',
            author=TaskCreateFormTests.user,
        )
        cls.comment = Comment.objects.create(
            post=TaskCreateFormTests.post,
            author=TaskCreateFormTests.user,
            text='блабла'
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        posts_count = Post.objects.count()
        image_name = 'small.gif'
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name=image_name,
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'форма создания поста',
            'group': self.group.id,
            'image': uploaded
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse('posts:profile',
                             kwargs={'username': self.user.username}),)
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                author=self.user,
                group=self.group.id,
                image=f'posts/{image_name}'
            ).exists()
        )

    def test_edit_post(self):
        post_id = f'{TaskCreateFormTests.post.id}'
        post_count = Post.objects.count()
        image_name = 'big.gif'
        big_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name=image_name,
            content=big_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'новый пост',
            'group': self.group.id,
            'image': uploaded
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit',
                    kwargs={'post_id': post_id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse('posts:post_detail',
                             kwargs={'post_id': post_id}),)
        self.assertEqual(Post.objects.count(), post_count)
        self.assertTrue(
            Post.objects.filter(
                text=form_data['text'],
                author=self.user,
                group=self.group.id,
                image=f'posts/{image_name}'
            ).exists()
        )

    def test_authorized_user_comment(self):
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'блабла'
        }
        self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comment_count + 1)

    def test_unauthorized_user_comment(self):
        comment_count = Comment.objects.count()
        form_data = {
            'text': 'блабла'
        }
        self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comment_count)
