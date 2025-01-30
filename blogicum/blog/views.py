from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import (ListView, UpdateView, DeleteView, DetailView,
                                  CreateView)
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone as tz
from django.db.models import Count
from django.http import Http404

from .constants import PAGINATE_COUNT
from .forms import CommentForm, PostForm, UserForm
from blog.models import Comment, Post, Category


def filters_post(manage):
    return manage.filter(
        pub_date__lt=tz.now(),
        is_published=True,
        category__is_published=True,
    ).annotate(comment_count=Count('comments'))


class IndexListView(ListView):
    model = Post
    queryset = filters_post(Post.objects.prefetch_related(
        'comments')).select_related('author')
    template_name = 'blog/index.html'
    ordering = '-pub_date'
    paginate_by = PAGINATE_COUNT


@login_required
def add_comment(request, post_id):
    comment = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST)
    if form.is_valid():
        commentary = form.save(commit=False)
        commentary.author = request.user
        commentary.post = comment
        commentary.save()
    return redirect('blog:post_detail', post_id=post_id)


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class CommentMixin:
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'
    comment = None

    def dispatch(self, request, *args, **kwargs):
        instance = get_object_or_404(
            Comment, pk=kwargs.get(
                'comment_id'
            )
        )
        if instance.author != request.user:
            return redirect('blog:post_detail', self.kwargs.get('comment_id'))
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy('blog:post_detail',
                            kwargs={'post_id': self.kwargs.get('post_id')})

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.comment = self.comment
        return super().form_valid(form)


class CategoryListView(ListView):
    model = Post
    template_name = 'blog/category.html'
    paginate_by = PAGINATE_COUNT

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = get_object_or_404(
            Category,
            slug=self.kwargs['category_slug'],
            is_published=True,
        )
        return context

    def get_queryset(self):
        category_slug = self.kwargs.get('category_slug')
        category = get_object_or_404(
            Category,
            slug=category_slug,
            is_published=True
        )

        queryset = filters_post(category.posts).order_by('-pub_date')
        return queryset


class CommentUpdateView(LoginRequiredMixin,
                        CommentMixin, UpdateView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        return context


class CommentDeleteView(LoginRequiredMixin, CommentMixin, DeleteView):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_delete'] = True
        return context


class ProfileListView(ListView):
    model = Post
    template_name = 'blog/profile.html'
    ordering = 'id'
    paginate_by = PAGINATE_COUNT

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = get_object_or_404(User, username=self.kwargs.get(
            'username')
        )
        return context

    def get_queryset(self):
        author = get_object_or_404(User, username=self.kwargs.get('username'))
        instance = author.posts.filter(
            author=author
        ).annotate(
            comment_count=Count('comments')
        ).order_by('-pub_date')
        return instance


class ProfiletUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserForm
    template_name = 'blog/user.html'
    success_url = reverse_lazy('blog:index')

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.save()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            'blog:profile',
            kwargs={'username': self.request.user.username})


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'
    ordering = ('-pub_date',)
    paginate_by = PAGINATE_COUNT
    context_object_name = 'post'
    pk_url_kwarg = 'post_id'

    def get_object(self):
        object = super(PostDetailView, self).get_object()
        if self.request.user != object.author and (
            not object.is_published or not object.category.is_published
        ):
            raise Http404()
        return object

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = self.object.comments.select_related('author')
        return context


class PostMixin:
    def dispatch(self, request, *args, **kwargs):
        instance = get_object_or_404(Post, pk=kwargs.get('post_id'))
        if instance.author != request.user:
            return redirect('blog:post_detail', self.kwargs.get('post_id'))
        return super().dispatch(request, *args, **kwargs)


class PostDeleteView(PostMixin, LoginRequiredMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    success_url = reverse_lazy('blog:index')
    pk_url_kwarg = 'post_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_delete'] = True
        return context


class PostUpdateView(PostMixin, LoginRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = True
        return context
