# -*- coding: utf-8 -*-
from ikwen.theming.models import Theme

__author__ = 'Roddy Mbogning'

from django.db import models
from ikwen.core.models import AbstractConfig
from ikwen.core.utils import to_dict


class OperatorProfile(AbstractConfig):
    max_objects = models.IntegerField(default=100,
                                       help_text="Max number of products this provider may have.")
    theme = models.ForeignKey(Theme, blank=True, null=True)
    max_products = models.IntegerField(default=100)


    class Meta:
        verbose_name = "Operator"
        verbose_name_plural = "Operators"

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
