import os
import random
from time import strftime

from django.db import models
from datetime import datetime
# Create your models here.
from django.utils import translation

from django.conf import settings
from djangotoolbox.fields import ListField, EmbeddedModelField
from ikwen.core.fields import MultiImageField
from ikwen.core.models import Model
from ikwen.core.utils import to_dict, add_database_to_settings
from ikwen.accesscontrol.models import Member


class PostCategory(Model):
    name = models.CharField(max_length=240, blank=False, unique=True)
    slug = models.SlugField(max_length=240, blank=False, unique=True)
    is_active = models.BooleanField(default=False)

    def __unicode__(self):
        return "%s" % self.name

    class Meta:
        verbose_name_plural = "Categories"

    def _get_posts_count(self):
        return Post.objects.filter(is_active=True, category=self).count()

    post_count = property(_get_posts_count)


class Post(Model):
    UPLOAD_TO = 'blog/blog_img'
    category = models.ForeignKey(PostCategory, blank=True, null=True)
    title = models.CharField(max_length=240, blank=False, unique=True)
    summary = models.CharField(max_length=240, blank=True)
    slug = models.SlugField(max_length=240, blank=False, unique=True, editable=False)
    image = MultiImageField(upload_to=UPLOAD_TO, blank=True, null=True, max_size=800)
    entry = models.TextField()
    pub_date = models.DateField(default=datetime.now, editable=False)
    appear_on_home_page = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    member = models.ForeignKey(Member, editable=False)
    tags = models.CharField(max_length=255, blank=True)
    likes = models.SmallIntegerField(default=0, editable=False)
    linked_document = models.FileField(blank=True, upload_to=UPLOAD_TO)
    rand = models.FloatField(default=random.random, db_index=True, editable=False)
    consult_count = models.IntegerField(default=10)

    def __unicode__(self):
        return "%s" % self.title

    def get_path(self):
        folders = '%s' % (self.slug)
        return '%s' % folders

    def get_uri(self):
        base_uri = getattr(settings, 'BASE_URI')
        return '%s%s' % (base_uri, self.get_path())

    def get_image_url(self):
        if self.image:
            return self.image.url
        else:
            return None

    def delete(self, *args, **kwargs):
        for photo in self.image:
            photo.delete(*args, **kwargs)


class PostLikes(Model):
    member = models.ForeignKey(Member)
    post = models.ForeignKey(Post)


class Comment(models.Model):
    email = models.EmailField()
    name = models.CharField(max_length=45, blank=True)
    post = models.ForeignKey(Post)
    entry = models.TextField()
    created_on = models.DateField(default=datetime.now)
    is_active = models.BooleanField(default=False)

    def get_display_date(self):
        return strftime("%b.%d %Y", self.created_on)

    def to_dict(self):
        display_date = self.get_display_date()
        var = to_dict(self)
        var['publ_date'] = display_date
        del(var['created_on'])


class Photo(models.Model):
    UPLOAD_TO = 'blog/blog_img'
    PLACE_HOLDER = 'no_photo.png'
    image = MultiImageField(upload_to=UPLOAD_TO, max_size=800)

    def delete(self, *args, **kwargs):
        try:
            os.unlink(self.image.path)
            os.unlink(self.image.small_path)
            os.unlink(self.image.thumb_path)
        except:
            pass
        super(Photo, self).delete(*args, **kwargs)

    def __unicode__(self):
        return self.image.url


class LinkedDoc(models.Model):
    UPLOAD_TO = 'blog/blog_img'
    PLACE_HOLDER = 'no_photo.png'
    document = models.FileField(upload_to=UPLOAD_TO)

    def delete(self, *args, **kwargs):
        try:
            os.unlink(self.document.path)
        except:
            pass
        super(LinkedDoc, self).delete(*args, **kwargs)

    def __unicode__(self):
        return self.document.url

    def extension(self):
        name, extension = os.path.splitext(self.document.name)
        return extension

