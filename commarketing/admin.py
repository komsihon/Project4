from django.contrib import admin
from django.utils.translation import gettext as _


class BannerAdmin(admin.ModelAdmin):
    fields = ('title', 'cta', 'target_url', )


class SmartCategoryAdmin(admin.ModelAdmin):
    fields = ('title', 'content_type',)


class HomepageSectionAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('title', 'content_type')}),
        (_("Details"), {'fields': ('description', 'cta', 'target_url', 'text_position', 'background_image')}),
    )
    fields = ('title', 'content_type', 'description', 'cta', 'target_url', 'text_position', 'background_image',)
