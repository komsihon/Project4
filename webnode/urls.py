from django.conf.urls import patterns, include, url

from django.contrib import admin
from ikwen_webnode.webnode.views import Home, ItemList, ItemDetails, DeployCloud, Registration, appSignIn

from django.conf import settings

admin.autodiscover()

if getattr(settings, 'IS_IKWEN', False) or getattr(settings, 'IS_APP_RETAILER', False):
    urlpatterns = patterns(
        '',
        url(r'^deployCloud/$', DeployCloud.as_view(), name='deploy_cloud')
    )
else:
    urlpatterns = patterns(
        '',
        url(r'^$', Home.as_view(), name='home'),
        url(r'^appRegister/$', Registration.as_view(), name='app_register'),
        url(r'^appSignIn/$', appSignIn.as_view(), name='app_login'),
        url(r'^(?P<category_slug>[-\w]+)/(?P<slug>[-\w]+)/$', ItemDetails.as_view(), name='product_details'),
        url(r'^(?P<slug>[-\w]+)/$', ItemList.as_view(), name='item_list'),
    )
