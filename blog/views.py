import os

from ajaxuploader.views import AjaxFileUploader
from django.contrib.admin.sites import AdminSite
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.urlresolvers import reverse
from django.forms.models import modelform_factory
from django.http.response import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.contrib.admin import helpers
from django.contrib import messages
from django.utils.translation import gettext as _

# Create your views here.
import random

from django.core.files import File
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import TemplateView
from ikwen.accesscontrol.templatetags.auth_tokens import append_auth_tokens

from ikwen.core.utils import get_model_admin_instance, DefaultUploadBackend
from ikwen_kakocase.commarketing.models import SmartCategory
from ikwen_webnode.blog.admin import PostAdmin, CategoryAdmin
from ikwen_webnode.blog.models import Post, Comments, PostCategory, PostLikes, Photo
from django.http import HttpResponse
import json
from django.template.defaultfilters import slugify
from ikwen.core.views import HybridListView
from ikwen_webnode.webnode.views import TemplateSelector

from conf import settings

POST_PER_PAGE = 5
MEDIA_DIR = settings.MEDIA_ROOT + 'tiny_mce/'
TINYMCE_MEDIA_URL = settings.MEDIA_URL + 'tiny_mce/'


class BlogBaseView(TemplateSelector, TemplateView):
    def get_context_data(self, **kwargs):
        context = super(BlogBaseView, self).get_context_data(**kwargs)
        rand = random.random()
        suggestions = Post.objects.filter(is_active=True, rand__lte=rand)
        categories = PostCategory.objects.all()
        recent_posts = Post.objects.filter(is_active=True).order_by('created_on')[:5]
        context['categories'] = categories
        context['recent_posts'] = recent_posts
        context['suggestions'] = suggestions[:4]
        context['most_consulted'] = recent_posts[:4]
        context['archives'] = recent_posts
        return context


class PostsList(BlogBaseView):
    template_name = 'blog/home.html'

    def get_context_data(self, **kwargs):
        context = super(PostsList, self).get_context_data(**kwargs)
        posts = Post.objects.filter(is_active=True)
        entries = posts.order_by('-pub_date')
        page_count = entries.count() / POST_PER_PAGE
        for entry in entries:
            comment_count = Comments.objects.filter(post=entry).count()
            entry.comment_count = comment_count
        context['items_paginated'] = get_paginated_view(self.request, entries, POST_PER_PAGE)
        context['entries'] = entries
        context['page_count'] = page_count
        return context


class Search(BlogBaseView):
    template_name = 'blog/search.html'

    def get_context_data(self, **kwargs):
        context = super(Search, self).get_context_data(**kwargs)
        radix = self.request.GET.get('radix')
        if radix == '':
            radix = "No-radix"

        entries = grab_items_by_radix(radix)
        context['items_paginated'] = get_paginated_view(self.request, entries, POST_PER_PAGE)
        context['pages'] = get_paginated_view(self.request, entries, POST_PER_PAGE)
        context['entries'] = entries
        context['radix'] = radix
        return context


class PostPerCategory(BlogBaseView):
    template_name = 'blog/search.html'

    def get_context_data(self, **kwargs):
        context = super(PostPerCategory, self).get_context_data(**kwargs)
        category_slug = kwargs['category_slug']
        category = PostCategory.objects.get(slug=category_slug)
        radix = 'for ' + category.name + ' category'

        entries = Post.objects.filter(category=category)
        context['items_paginated'] = get_paginated_view(self.request, entries, POST_PER_PAGE)
        context['pages'] = get_paginated_view(self.request, entries, POST_PER_PAGE)
        context['entries'] = entries
        context['radix'] = radix
        return context


class PostDetails(BlogBaseView):
    template_name = 'blog/blog-item.html'

    def get_context_data(self, **kwargs):
        context = super(PostDetails, self).get_context_data(**kwargs)
        slug = kwargs['post_slug']
        entry = get_object_or_404(Post, slug=slug)
        context['comments'] = Comments.objects.filter(post=entry, is_active=True).order_by('id')
        context['blog'] = entry
        context['blog_uri'] = self.request.META['HTTP_REFERER']

        return context


def get_paginated_view(rq, items, nos):
    items_paginated = True
    paginator = Paginator(items, nos)
    page = rq.GET.get('page')
    try:
        items_paginated = paginator.page(page)
    except PageNotAnInteger:
        items_paginated = paginator.page(1)
    except EmptyPage:
        items_paginated = paginator.page(paginator.num_pages)
    return items_paginated


def save_comment(request, *args, **kwargs):
    post_id = request.GET.get('post_id')
    email = request.GET.get('email')
    name = request.GET.get('name')
    entry = request.GET.get('comment')
    post = get_object_or_404(Post, pk=post_id)
    comment = Comments(post=post, name=name, email=email, entry=entry)
    comment.save()
    response = {
        'email': comment.email,
        'name': comment.name,
        'entry': comment.entry,
        'publ_date': comment.get_display_date()
    }
    return HttpResponse(
        json.dumps(response),
        'content-type: text/json',
        **kwargs
    )


def save_post_likes(request, *args, **kwargs):
    member = request.user
    post_id = request.GET.get('post_id')
    liked_post = Post.objects.get(pk=post_id)
    if request.user.is_anonymous():
        return HttpResponse(
            json.dumps({'error': "must login before like"}),
            'content-type: text/json',
            **kwargs
        )
    try:
        PostLikes.objects.get(member=member, post=liked_post)
    except PostLikes.DoesNotExist:
        post_like = PostLikes.objects.get(member=member, post=liked_post)
        post_like.save()
        post_likes_count = liked_post.likes + 1
        liked_post.likes = post_likes_count
        liked_post.save()
        response = {
            'likes': post_likes_count,
        }
    else:
        response = {
            'error': "You have already liked this post",
        }
    return HttpResponse(
        json.dumps(response),
        'content-type: text/json',
        **kwargs
    )


def grab_items_by_radix(radix):
    items = []
    if radix is not None:
        radix.split(' ')
        posts_per_title = Post.objects.filter(title__icontains=radix, is_active=True)
        posts_per_tags = Post.objects.filter(tags__icontains=radix, is_active=True)
        posts_per_summary = Post.objects.filter(summary__icontains=radix, is_active=True)
        posts_per_desc = Post.objects.filter(entry__icontains=radix, is_active=True)
        posts = posts_per_title | posts_per_tags | posts_per_summary | posts_per_desc
        items.extend([post for post in posts])
    return items
    # else:
    #     posts = Post.objects.filter(is_active=True)


class ListCategory(HybridListView):
    template_name = 'blog/admin/category_list.html'
    model = PostCategory
    ordering = ('-id',)
    search_field = 'name'
    context_object_name = 'category_list'

    def get_context_data(self, **kwargs):
        context = super(ListCategory, self).get_context_data(**kwargs)
        categories = PostCategory.objects.all()
        context['categories'] = categories
        return context


class ChangeCategory(TemplateView):
    template_name = 'blog/admin/change_category.html'

    def get_context_data(self, **kwargs):
        context = super(ChangeCategory, self).get_context_data(**kwargs)
        category_id = kwargs.get('category_id')  # May be overridden with the one from GET data
        category_id = self.request.GET.get('category_id', category_id)
        category = None
        if category_id:
            category = get_object_or_404(PostCategory, pk=category_id)
        category_admin = get_model_admin_instance(PostCategory, CategoryAdmin)
        ModelForm = modelform_factory(PostCategory, fields=('name', 'slug', 'is_active'))
        form = ModelForm(instance=category)
        category_form = helpers.AdminForm(form, list(category_admin.get_fieldsets(self.request)),
                                          category_admin.get_prepopulated_fields(self.request),
                                          category_admin.get_readonly_fields(self.request, obj=category))
        context['category'] = category
        context['model_admin_form'] = category_form
        return context

    def post(self, request, *args, **kwargs):
        category_id = self.request.POST.get('category_id')
        category = None
        if category_id:
            category = get_object_or_404(PostCategory, pk=category_id)
        category_admin = get_model_admin_instance(PostCategory, CategoryAdmin)
        ModelForm = category_admin.get_form(self.request)
        form = ModelForm(request.POST, instance=category)
        if form.is_valid():
            name = form.cleaned_data['name']
            slug = slugify(name)
            if category_id:
                category = PostCategory(name=name)
                category.save()
            else:
                category.name = name
                category.slug = slug
                category.is_active = True if request.POST.get('is_active') else False
                category.save()
            if category_id:
                next_url = reverse('blog:change_category', args=(category_id, ))
                messages.success(request, _("Category %s successfully updated." % category.name))
            else:
                next_url = self.request.REQUEST.get('next')
                if not next_url:
                    next_url = reverse('blog:category_list')
                messages.success(request, _("Category %s successfully created." % category.name))
            return HttpResponseRedirect(next_url)
        else:
            context = self.get_context_data(**kwargs)
            context['errors'] = form.errors
            return render(request, self.template_name, context)


class AdminPostHome(HybridListView):
    template_name = 'blog/admin/admin_blog_list.html'

    model = Post
    search_field = 'title'
    ordering = ('-updated_on',)
    context_object_name = 'entries'

    def get(self, request, *args, **kwargs):
        sorted_keys = request.GET.get('sorted')
        if sorted_keys:
            for token in sorted_keys.split(','):
                try:
                    Post.objects.all()
                except:
                    continue
            return HttpResponse(json.dumps({'success': True}), 'content-type: text/json')
        return super(AdminPostHome, self).get(request, *args, **kwargs)


class ChangePost(TemplateView):
    template_name = 'blog/admin/admin_change_blog.html'

    def get_post_admin(self):
        default_site = AdminSite()
        post_admin = PostAdmin(Post, default_site)
        return post_admin

    def get_context_data(self, **kwargs):
        context = super(ChangePost, self).get_context_data(**kwargs)
        post_id = kwargs.get('post_id')  # May be overridden with the one from GET data
        post_id = self.request.GET.get('post_id', post_id)
        post = None
        if post_id:
            post = get_object_or_404(Post, pk=post_id)
        post_admin = get_model_admin_instance(Post, PostAdmin)
        ModelForm = modelform_factory(Post, fields=('category', 'title', 'summary', 'entry', 'is_active', 'appear_on_home_page'))
        form = ModelForm(instance=post)
        post_form = helpers.AdminForm(form, list(post_admin.get_fieldsets(self.request)),
                                      post_admin.get_prepopulated_fields(self.request),
                                      post_admin.get_readonly_fields(self.request, obj=post))
        context['post'] = post
        context['model_admin_form'] = post_form
        return context

    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    def post(self, request, *args, **kwargs):
        post_id = self.request.POST.get('post_id')
        post = None
        member = request.user
        if post_id:
            post = get_object_or_404(Post, pk=post_id)
        post_admin = get_model_admin_instance(Post, PostAdmin)
        ModelForm = post_admin.get_form(self.request)
        form = ModelForm(request.POST, instance=post)
        if form.is_valid():
            title = request.POST.get('title')
            category_id = request.POST.get('category')
            summary = request.POST.get('summary')
            entry = request.POST.get('entry')
            is_active = request.POST.get('is_active')
            image_url = request.POST.get('image_url')
            post_category = PostCategory.objects.get(pk=category_id)
            # media_link = request.POST.get('media_link')
            if not post:
                post = Post(title=title, summary=summary, entry=entry, is_active=is_active, member=member)
                post.slug = slugify(title)
                post.category = post_category
                post.save()
            else:
                post.title = title
                post.slug = slugify(title)
                post.entry = entry
                post.summary = summary
                post.is_active = True if request.POST.get('is_active') else False
            if image_url:
                if not post.image.name or image_url != post.image.url:
                    filename = image_url.split('/')[-1]
                    media_root = getattr(settings, 'MEDIA_ROOT')
                    media_url = getattr(settings, 'MEDIA_URL')
                    image_url = image_url.replace(media_url, '')
                    try:
                        with open(media_root + image_url, 'r') as f:
                            content = File(f)
                            destination = media_root + Post.UPLOAD_TO + "/" + filename
                            post.image.save(destination, content)
                        os.unlink(media_root + image_url)
                    except IOError as e:
                        if getattr(settings, 'DEBUG', False):
                            raise e
                        return {'error': 'File failed to upload. May be invalid or corrupted image file'}
            post.save()
            if post_id:
                next_url = reverse('blog:change_post', args=(post_id,)) + '?success=yes'
                messages.success(request, _("Post %s successfully updated." % post.title))
            else:
                next_url = reverse('blog:list_post') + '?success=yes'
            next_url = append_auth_tokens(next_url, request)
            return HttpResponseRedirect(next_url)
        else:
            context = self.get_context_data(**kwargs)
            context['errors'] = form.errors
            return render(request, self.template_name, context)


class PostPhotoUploadBackend(DefaultUploadBackend):
    """
    Ajax upload handler for :class:`kako.models.Product` photos
    """

    def upload_complete(self, request, filename, *args, **kwargs):
        path = self.UPLOAD_DIR + "/" + filename
        self._dest.close()
        media_root = getattr(settings, 'MEDIA_ROOT')
        try:
            with open(media_root + path, 'r') as f:
                content = File(f)
                destination = media_root + Photo.UPLOAD_TO + "/" + filename
                photo = Photo()
                photo.image.save(destination, content)
                post_id = request.GET.get('post_id')
                if post_id:
                    try:
                        post = Post.objects.get(pk=post_id)
                        post.image.append(photo)
                        post.save()
                    except:
                        pass

            os.unlink(media_root + path)
            return {
                'id': photo.id,
                'url': photo.image.small_url
            }
        except IOError as e:
            if getattr(settings, 'DEBUG', False):
                raise e
            return {'error': 'File failed to upload. May be invalid or corrupted image file'}


post_photo_uploader = AjaxFileUploader(PostPhotoUploadBackend)


def delete_photo(request, *args, **kwargs):
    post_id = request.GET.get('post_id')
    photo_id = request.GET['photo_id']
    photo = Photo(id=photo_id)
    if post_id:
        post = Post.objects.get(pk=post_id)
        if photo in post.image:
            post.image.remove(photo)
            post.save()
    try:
        Photo.objects.get(pk=photo_id).delete()
    except:
        pass
    return HttpResponse(
        json.dumps({'success': True}),
        content_type='application/json')


def load_posts_for_homepage(request, *args, **kwargs):
    entries = Post.objects.filter(is_active=True)
    # entries = posts.order_by('-pub_date')
    for entry in entries:
        comment_count = Comments.objects.filter(post=entry).count()
        entry.comment_count = comment_count
    context = {'entries': entries}
    return render(request, 'webnode/snippets/homepage_section_blog.html', context)


class CommentList(HybridListView):
    template_name = 'blog/admin/admin_blog_comments_list.html'
    html_results_template_name = 'blog/snippets/comment_list_results.html'
    queryset = Comments.objects.all()
    ordering = ('-pub_date', )
    context_object_name = 'Comments_list'

    def get_context_data(self, **kwargs):
        queryset = self.get_queryset()
        context = super(CommentList, self).get_context_data(**kwargs)
        paginator = Paginator(queryset, self.page_size)
        objects_page = paginator.page(1)
        context['q'] = self.request.GET.get('q')
        context['objects_page'] = objects_page
        return context


def toggle_object_attribute(request, *args, **kwargs):
    object_id = request.GET['object_id']
    attr = request.GET['attr']
    val = request.GET['val']
    try:
        obj = Comments.objects.get(pk=object_id)
    except Comments.DoesNotExist:
        obj = Comments.objects.get(pk=object_id)
    if val.lower() == 'true':
        obj.__dict__[attr] = True
    else:
        obj.__dict__[attr] = False
    obj.save()
    response = {'success': True}
    return HttpResponse(json.dumps(response), 'content-type: text/json')


def delete_comment_object(request, *args, **kwargs):
    pk = request.GET.get('selection')
    try:
        Comments.objects.get(pk=pk).delete()
        message = "Item successfully deleted."
    except Comments.DoesNotExist:
        try:
            Comments.objects.get(pk=pk).delete()
            message = "Item successfully deleted."
        except Comments.DoesNotExist:
            message = "Object was not found."

    response = {'message': message}
    return HttpResponse(json.dumps(response), 'content-type: text/json')


def get_media(request, *args, **kwargs):
    media_list = []
    for root, dirs, files in os.walk(MEDIA_DIR):
        for filename in files:
            if filename.lower():
                filename = TINYMCE_MEDIA_URL + filename
                media_list.append(os.path.join(filename))
    response = {
        'media_list': media_list,
    }
    return HttpResponse(
        json.dumps(response),
        'content-type: text/json',
        **kwargs
    )


def delete_photo_list(request, *args, **kwargs):
    filename = request.GET.get('filename')
    file_path = ''
    if filename:
        file_path = filename.replace(settings.MEDIA_URL, settings.MEDIA_ROOT)
    try:
        os.remove(file_path)
        return HttpResponse(
            json.dumps({'success': True}),
            content_type='application/json'
        )
    except:
        response = "Error: %s file not found" % filename
        return HttpResponse(
            json.dumps({'error': response}),
            content_type='application/json'
        )


