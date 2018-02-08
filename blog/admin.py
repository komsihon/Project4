# -*- coding: utf-8 -*-
from django.contrib import admin
from ikwen_webnode.blog.models import Post, PostCategory


class PostCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'post_count',)
    fields = ('name', )


class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active',)
    search_fields = ('title',)
    # prepopulated_fields = {"slug": ("title",)}

    fields = ('title', 'category', 'summary', 'entry', 'is_active', 'appear_on_home_page')

#
# admin.site.register(Post, PostAdmin)
# admin.site.register(PostCategory, CategoryAdmin)
