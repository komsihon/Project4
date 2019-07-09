from django.contrib import admin
from django.utils.translation import gettext as _


class BannerAdmin(admin.ModelAdmin):
    fields = ('title', 'cta', 'target_url',  'description',)


class SmartCategoryAdmin(admin.ModelAdmin):
    fields = ('title', 'content_type', 'target_url', 'description',)


class HomepageSectionAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('title', 'content_type', 'density')}),
        (_("Details"), {'fields': ('description', 'cta', 'target_url', 'text_position', 'background_image')}),
    )
    fields = ('title', 'content_type', 'density', 'description', 'cta', 'target_url', 'text_position', 'background_image',)
