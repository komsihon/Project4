# -*- coding: utf-8 -*-
from django.contrib import admin
from ikwen_webnode.blog.models import Post, PostCategory


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'post_count',)
    prepopulated_fields = {"slug": ("name",)}


class PostAdmin(admin.ModelAdmin):
    list_display = ('title', 'publish',)
    search_fields = ('title',)
    # prepopulated_fields = {"slug": ("title",)}

    fields = ('title', 'category', 'summary', 'entry', 'publish')

#
# admin.site.register(Post, PostAdmin)
# admin.site.register(PostCategory, CategoryAdmin)
