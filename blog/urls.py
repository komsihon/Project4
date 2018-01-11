from django.conf.urls import patterns, include, url

from django.contrib import admin
from django.contrib.auth.decorators import permission_required

from ikwen_webnode.blog.views import PostDetails, Search, PostPerCategory, PostsList, save_comment, AdminBlogHome,\
    ChangeBlog, save_post_likes, post_photo_uploader, delete_photo
from ikwen_webnode.webnode.views import AdminHome


admin.autodiscover()

urlpatterns = patterns(
    '',
    # url(r'^change_product/$', permission_required('webnode.ik_manage_content')(ChangeProduct.as_view()), categories, name='change_product'),
    url(r'^listBlogPost/$', permission_required('webnode.ik_manage_content')(AdminBlogHome.as_view()), name='list_blog'),
    url(r'^changeBlogPost/$', permission_required('webnode.ik_manage_content')(ChangeBlog.as_view()), name='change_blog'),
    url(r'^changeBlogPost/(?P<post_id>[-\w]+)/$', permission_required('webnode.ik_manage_content')(ChangeBlog.as_view()),
        name='changeBlogPost'),
    url(r'^post_photo_uploader$', post_photo_uploader, name='post_photo_uploader'),
    url(r'^delete_photo$', delete_photo, name='delete_photo'),

    url(r'^(?P<post_slug>[-\w]+)/$', PostDetails.as_view(), name='details'),
    url(r'^search$', Search.as_view(), name='search'),
    url(r'^category/(?P<category_slug>[-\w]+)/$', PostPerCategory.as_view(), name='post_per_category'),
    url(r'^yommax/$', AdminHome.as_view(), name='admin_home'),
    url(r'^$', PostsList.as_view(), name='home'),
    url(r'^save_comment$', save_comment, name='save_comment'),
    url(r'^save_post_likes$', save_post_likes, name='save_post_likes'),

)
