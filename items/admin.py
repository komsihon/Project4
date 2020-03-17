from django.contrib.admin.sites import AlreadyRegistered
from django.template.defaultfilters import slugify
from ikwen.core.admin import CustomBaseAdmin
from import_export import resources

from ikwen.core.utils import get_service_instance
from ikwen_webnode.items.models import Item, RecurringPaymentService, ItemCategory
from django.contrib import admin

from ikwen_kakocase.kakocase.models import IS_RETAILER

from django.conf import settings


class ItemResource(resources.ModelResource):

    def import_field(self, field, obj, data):
        if field.column_name == 'category':
            slug = slugify(data['category'])
            try:
                category = ItemCategory.objects.get(slug=slug)
            except ItemCategory.DoesNotExist:
                name = data['category']
                from items.utils import create_category
                category = create_category(name)
            data['category'] = category.id
        super(ItemResource, self).import_field(field, obj, data)

    def before_save_instance(self, instance, dry_run):
        slug = slugify(instance.name)
        instance.slug = slug
        instance.tags = slug.replace('-', ' ')
        instance.visible = False
        instance.batch_upload = self.batch_upload

    def skip_row(self, instance, original):
        try:
            if instance.reference:
                Item.objects.get(reference=instance.reference)
                return True
            return False
        except Item.DoesNotExist:
            return False

    class Meta:
        model = Item
        skip_unchanged = True
        # fields = ('category', 'name', 'reference', 'wholesale_price', 'retail_price', 'max_price')


class ItemAdmin(admin.ModelAdmin):
    fieldsets = (
        (None, {'fields': ('provider', 'category', 'name', 'brand', 'wholesale_price', 'video_url', 'retail_price',
                           'max_price', 'size', 'color', 'weight', 'badge_text', 'stock', 'visible', 'summary',
                           'description', ) if IS_RETAILER
        else ('category', 'name', 'brand', 'wholesale_price', 'video_url', 'retail_price', 'max_price',
              'size', 'color', 'weight', 'stock', 'unit_of_measurement', 'min_order', 'badge_text', 'summary',
              'description', 'visible', 'has_background_image')}),
    )

    def get_readonly_fields(self, request, obj=None):
        ro = ['provider', 'brand', 'wholesale_price', 'max_price', 'size', 'color', 'weight', 'stock']
        return ro


class RecurringPaymentServiceAdmin(CustomBaseAdmin):
    readonly_fields = ('provider', )


class ItemCategoryAdmin(admin.ModelAdmin):
    if getattr(settings, 'IS_IKWEN', False):
        list_display = ('name', 'description', 'total_items_traded', 'total_orders_count',)
        fields = ('name', 'description', 'total_items_traded', 'total_orders_count',)
        readonly_fields = ('total_items_traded', 'total_orders_count',)
    else:
        fields = ('name','content_type', 'description', 'badge_text', 'is_active',)
