from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Follow, Group, Post, User


def index(request):
    post_list = Post.objects.all().order_by('-pub_date')
    paginator = Paginator(post_list, settings.COUNT_PAGES)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_show(request, slug):
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.order_by('-pub_date')
    paginator = Paginator(posts, settings.COUNT_PAGES)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    user = get_object_or_404(User, username=username)
    post_list = user.posts.order_by('-pub_date').all()
    paginator = Paginator(post_list, settings.COUNT_PAGES)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    if request.user.is_authenticated:
        following = Follow.objects.filter(
            user=request.user,
            author=user,
        ).exists()
    else:
        following = None
    context = {
        'page_obj': page_obj,
        'author': user,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, username, post_id):
    user_post = get_object_or_404(Post, id=post_id)
    form = CommentForm()
    comments = user_post.comments.all()
    context = {
        'post': user_post,
        'form': form,
        'comments': comments
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', username=request.user.username)
    context = {
        'form': form,
        'is_edit': False
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def post_edit(request, username, post_id):
    post = get_object_or_404(Post, id=post_id)
    if username != request.user.username:
        return redirect('posts:post_detail', username=username,
                        post_id=post)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', username=username,
                        post_id=post.id)
    context = {
        'form': form,
        'is_edit': True,
        'post': post,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, username, post_id):
    post = post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', username=username, post_id=post.id)


@login_required
def follow_index(request):
    post_list = (Post.objects.filter(author__following__user=request.user).
                 order_by('-pub_date'))
    paginator = Paginator(post_list, settings.COUNT_PAGES)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {'page_obj': page_obj}

    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    if username != request.user.username:
        followed_author = get_object_or_404(User, username=username)
        Follow.objects.get_or_create(user=request.user, author=followed_author)

    return redirect('posts:profile', username=username)


@login_required
def profile_unfollow(request, username):
    followed_author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=followed_author).delete()

    return redirect('posts:profile', username=username)
