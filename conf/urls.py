from django.conf.urls import patterns, include, url

from django.contrib import admin
from ikwen_webnode.webnode.views import *
admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^laakam/', include(admin.site.urls)),
    url(r'^blog/', include('ikwen_webnode.blog.urls', namespace='blog')),
    url(r'^ikwen/theming/', include('ikwen.theming.urls', namespace='theming')),
    url(r'^marketing/', include('ikwen_webnode.commarketing.urls', namespace='marketing')),
    url(r'^kakocase/', include('ikwen_kakocase.kakocase.urls', namespace='kakocase')),

    url(r'^$', Home.as_view(), name='home'),
    url(r'^dashboard/$', AdminHome.as_view(), name='admin_home'),
    url(r'^i18n/', include('django.conf.urls.i18n')),
    url(r'^ikwen/', include('ikwen.core.urls', namespace='ikwen')),
    url(r'^billing/', include('ikwen.billing.urls', namespace='billing')),
    url(r'^kako/', include('ikwen_kakocase.kako.urls', namespace='kako')),
    url(r'^page/(?P<url>[-\w]+)/$', FlatPageView.as_view(), name='flatpage'),
    url(r'^', include('ikwen_webnode.webnode.urls', namespace='webnode')),
)
