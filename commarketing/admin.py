from django.contrib import admin


class BannerAdmin(admin.ModelAdmin):
    fields = ('title', 'cta', 'target_url', )


class SmartCategoryAdmin(admin.ModelAdmin):
    fields = ('title', 'content_type', 'badge_text',)


class HomepageSectionAdmin(admin.ModelAdmin):
    fields = ('title', 'description', 'cta', 'text_position', 'background_image',)
