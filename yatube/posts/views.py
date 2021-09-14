from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Comment, Follow, Group, Post, User


def index(request):
    post_list = Post.objects.all().order_by('-pub_date')
    paginator = Paginator(post_list, settings.COUNT_PAGES)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
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
    post_amount = post_list.count()
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
        'post_amount': post_amount,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    user_post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    comments = Comment.objects.filter(post_id=post_id)
    post_amount = user_post.author.posts.all().count()
    text = user_post.text[0:30]
    context = {
        'post': user_post,
        'post_amount': post_amount,
        'text': text,
        'form': form,
        'comments': comments
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    groups = Group.objects.all()
    form = PostForm(request.POST or None, files=request.FILES or None)
    if request.method == 'POST':
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('posts:profile', username=request.user.username)
    context = {
        'form': form,
        'groups': groups,
        'is_edit': False
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    user = request.user
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )
    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect('posts:post_detail', post_id=post_id)
    groups = Group.objects.all()
    context = {
        'form': form,
        'groups': groups,
        'is_edit': True,
        'post': post,
        'user': user
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


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
