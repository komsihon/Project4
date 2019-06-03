# -*- coding: utf-8 -*-

__author__ = 'Roddy Mbogning'
from django.conf import settings
from djangotoolbox.admin import admin
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save

from ikwen_kakocase.kakocase.models import ProductCategory
from ikwen_webnode.webnode.models import OperatorProfile
from ikwen_kakocase.commarketing.models import SmartCategory
from ikwen.core.utils import get_service_instance


if getattr(settings, 'IS_IKWEN', False):
    _fieldsets = [
        (_('Company'), {'fields': ('company_name', 'short_description', 'slogan', 'latitude', 'longitude',
                                   'description', 'is_pro_version')}),
        (_('SMS'), {'fields': ('sms_api_script_url', )}),
        (_('Mailing'), {'fields': ('welcome_message', 'signature',)})
    ]
    # _readonly_fields = ('api_signature', )
else:
    service = get_service_instance()
    config = service.config
    _readonly_fields = ( 'is_pro_version',)
    _website_fields = {'fields': ()}
    _website_fields = {'fields': ('currency_code', 'currency_symbol')}

    _fieldsets = [
        (_('Company'), {'fields': ('company_name', 'short_description', 'slogan', 'description',)}),
        # (_('Website'), _website_fields),
        (_('Address & Contact'), {'fields': ('contact_email', 'contact_phone', 'address', 'country', 'city',
                                              'latitude', 'longitude',)}),
        (_('Social'), {'fields': ('facebook_link', 'twitter_link', 'google_plus_link', 'youtube_link', 'instagram_link',
                                  'tumblr_link', 'linkedin_link', )}),
        # (_('SMS'), {'fields': ('sms_sending_method', 'sms_api_script_url', 'sms_api_username', 'sms_api_password', )}),
        (_('Mailing'), {'fields': ('welcome_message', 'signature', )}),
    ]
    if config.is_pro_version:
        _fieldsets.extend([
            (_('External scripts'), {'fields': ('scripts', )}),
        ])


class OperatorProfileAdmin(admin.ModelAdmin):
    list_display = ('service', 'company_name')
    fieldsets = _fieldsets
    # readonly_fields = ('api_signature', )
    list_filter = ('company_name', 'contact_email', )
    save_on_top = True

    def delete_model(self, request, obj):
        self.message_user(request, "You are not allowed to delete Configuration of the platform")


def create_category_from_smart_category(instance, **kwargs):
    """
    here is the callback fired when the django signals detect a product save or a update
    when a product is save, we check if the stock is more than 0. And if it's the case, we rebuild the product tag to
    make it be readable during an end user search
    after all this, we then  build the availability objet and save it

    :param instance:
    :param kwargs:
    :return:
    """
    slug = instance.slug

    try:
        ProductCategory.objects.get(slug=slug)
    except ProductCategory.DoesNotExist:
        name = instance.title
        category = ProductCategory(name=name, slug=slug)
        category.save()
        instance.items_fk_list.append(category.id)
        instance.save()


post_save.connect(create_category_from_smart_category, sender=SmartCategory)


admin.site.register(OperatorProfile, OperatorProfileAdmin)