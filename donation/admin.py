# -*- coding: utf-8 -*-
from django.contrib import admin
from ikwen_webnode.donation.models import Donation


class DonationAdmin(admin.ModelAdmin):
    list_display = ('name', 'amount',)
    fields = ('name',  'amount',)