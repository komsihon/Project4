from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.contrib.auth.decorators import permission_required

from ikwen_webnode.blog.views import PostDetails, Search, PostPerCategory, PostsList, save_comment, AdminPostHome, \
    save_post_likes, post_photo_uploader,Post_document_uploader, delete_photo, ListCategory, ChangeCategory, load_posts_for_homepage, \
    ChangePost, CommentList, delete_comment_object, toggle_object_attribute, get_media, delete_tinyMCE_photo,delete_doc
from ikwen_webnode.webnode.views import AdminHome


admin.autodiscover()

urlpatterns = patterns(
    '',
    # url(r'^change_product/$', permission_required('webnode.ik_manage_content')(ChangeProduct.as_view()), categories, name='change_product'),
    url(r'^postlist/$', permission_required('webnode.ik_manage_content')(AdminPostHome.as_view()), name='list_post'),
    url(r'^postchange/$', permission_required('webnode.ik_manage_content')(ChangePost.as_view()), name='change_post'),
    url(r'^postchange/(?P<post_id>[-\w]+)/$', permission_required('webnode.ik_manage_content')(ChangePost.as_view()),
        name='change_post'),

    url(r'^list_categories/$', permission_required('webnode.ik_manage_content')(ListCategory.as_view()),name='list_category'),
    url(r'^changeCategory/$', permission_required('webnode.ik_manage_content')(ChangeCategory.as_view()), name='change_category'),
    url(r'^changeCategory/(?P<object_id>[-\w]+)/$', permission_required('webnode.ik_manage_content')(ChangeCategory.as_view()),name='change_category'),

    url(r'^listcomments/$', permission_required('webnode.ik_manage_content')(CommentList.as_view()),
        name='list_comment'),

    url(r'^post_photo_uploader$', post_photo_uploader, name='post_photo_uploader'),
    url(r'^post_doc_uploader$', Post_document_uploader, name='post_document_uploader'),
    url(r'^delete_photo$', delete_photo, name='delete_photo'),
    url(r'^delete_document$', delete_doc, name='delete_doc'),

    url(r'^(?P<post_slug>[-\w]+)/$', PostDetails.as_view(), name='details'),
    url(r'^search$', Search.as_view(), name='search'),
    url(r'^category/(?P<category_slug>[-\w]+)/$', PostPerCategory.as_view(), name='post_per_category'),
    url(r'^yommax/$', AdminHome.as_view(), name='admin_home'),
    url(r'^$', PostsList.as_view(), name='home'),
    url(r'^save_comment$', save_comment, name='save_comment'),
    url(r'^save_post_likes$', save_post_likes, name='save_post_likes'),
    url(r'^delete_promo_object$', delete_comment_object, name='delete_promo_object'),
    url(r'^toggle_object_attribute$', toggle_object_attribute, name='toggle_object_attribute'),
    url(r'^get_media$', get_media, name='get_media'),
    url(r'^delete_tinymce_photo', delete_tinyMCE_photo, name='delete_tinymce_photo'),
)
