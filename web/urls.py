
from django.conf.urls import patterns, url
from django.contrib.auth.decorators import permission_required

from ikwen_webnode.web.views import ChangeSmartObject, SmartCategoryList, delete_smart_object, \
    ChangeHomepageSection, set_smart_object_content, \
    BannerList, toggle_smart_object_attribute

urlpatterns = patterns(
    '',
    url(r'^banners/$', permission_required('web.ik_manage_marketing')(BannerList.as_view()), name='banner_list'),
    url(r'^menus/$', permission_required('web.ik_manage_marketing')(SmartCategoryList.as_view()), name='smart_category_list'),
    url(r'^smartObject/(?P<object_type>[-\w]+)/$', permission_required('web.ik_manage_marketing')(ChangeSmartObject.as_view()), name='change_smart_object'),
    url(r'^smartObject/(?P<object_type>[-\w]+)/(?P<smart_object_id>[-\w]+)/$', permission_required('web.ik_manage_marketing')(ChangeSmartObject.as_view()), name='change_smart_object'),
    url(r'^homepageSection/$', permission_required('web.ik_manage_marketing')(ChangeHomepageSection.as_view()), name='change_homepage_section'),
    url(r'^homepageSection/(?P<object_id>[-\w]+)/$', permission_required('web.ik_manage_marketing')(ChangeHomepageSection.as_view()), name='change_homepage_section'),
    url(r'^set_smart_object_content/(?P<action>[-\w]+)$', set_smart_object_content, name='set_smart_object_content'),
    url(r'^delete_smart_object$', delete_smart_object, name='delete_smart_object'),
    url(r'^toggle_smart_object_attribute$', toggle_smart_object_attribute, name='toggle_smart_object_attribute'),
)
