# -*- coding: utf-8 -*-
from django.conf import settings
from ikwen.theming.models import Theme

__author__ = 'Roddy Mbogning'

from django.db import models
from ikwen.core.models import AbstractConfig
from ikwen.core.utils import to_dict, add_database

PROVIDER_ADDED_ITEMS_EVENT = 'ProviderAddedProductsEvent'
PROVIDER_REMOVED_ITEM_EVENT = 'ProviderRemovedProductEvent'
PROVIDER_PUSHED_ITEM_EVENT = 'ProviderPushedProductEvent'


class OperatorProfile(AbstractConfig):
    max_objects = models.IntegerField(default=100,
                                      help_text="Max number of products this provider may have.")
    theme = models.ForeignKey(Theme, blank=True, null=True)
    max_products = models.IntegerField(default=100)
    ikwen_share_rate = models.IntegerField(default=0)
    ikwen_share_fixed = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Operator"
        verbose_name_plural = "Operators"

    def save(self, *args, **kwargs):
        if getattr(settings, 'IS_IKWEN', False):
            db = self.service.database
            add_database(db)
            try:
                obj_mirror = OperatorProfile.objects.using(db).get(pk=self.id)
                obj_mirror.currency_code = self.currency_code
                obj_mirror.currency_symbol = self.currency_symbol
                obj_mirror.cash_out_min = self.cash_out_min
                obj_mirror.is_pro_version = self.is_pro_version
                obj_mirror.can_manage_currencies = self.can_manage_currencies
                super(OperatorProfile, obj_mirror).save(using=db)
            except OperatorProfile.DoesNotExist:
                pass
        super(OperatorProfile, self).save(*args, **kwargs)

    def to_dict(self):
        var = to_dict(self)
        del (var['balance'])
        del (var['company_name_slug'])
        del (var['address'])
        del (var['short_description'])
        del (var['description'])
        del (var['slogan'])
        del (var['cash_out_min'])
        del (var['logo'])
        del (var['cover_image'])
        del (var['signature'])
        del (var['welcome_message'])
        del (var['facebook_link'])
        del (var['twitter_link'])
        del (var['google_plus_link'])
        del (var['youtube_link'])
        del (var['instagram_link'])
        del (var['tumblr_link'])
        del (var['linkedin_link'])
        del (var['scripts'])
        del (var['allow_paypal_direct'])
        del (var['sms_sending_method'])
        del (var['sms_api_script_url'])
        del (var['sms_api_username'])
        del (var['sms_api_password'])
        del (var['is_pro_version'])
        return var
