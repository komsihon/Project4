import os

from django.core.urlresolvers import reverse
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.utils.translation import gettext_lazy as _
from djangotoolbox.fields import ListField, EmbeddedModelField
from ikwen.accesscontrol.backends import UMBRELLA
from ikwen.core.fields import MultiImageField
from ikwen.core.models import AbstractWatchModel, Service
from ikwen.core.utils import to_dict, set_counters, increment_history_field
from ikwen_kakocase.kakocase.models import IS_PROVIDER, IS_RETAILER, PRODUCTS_PREVIEWS_PER_ROW

FLAT_PAGE = "FlatPage"
ITEM_LIST = "ItemList"
LINK = "Link"
MODULE = "Module"
SMART_CATEGORY_TYPE_CHOICES = (
    (FLAT_PAGE, _("Flat Page")),
    (ITEM_LIST, _("Item List")),
    (LINK, _("Link"))
)



wholesale_price_help_text = _("Your wholesale price. Retailers may set their own price.") if IS_PROVIDER\
    else _("Wholesale price of the provider")
retail_price_help_text = _("Price at which retailers must sell this item on their website. "
                           "If set, retailers will not be allowed to set their own price.") if IS_PROVIDER\
    else _("Your retail price.")
max_price_help_text = _("Maximum price at which retailers must sell this item on "
                        "their website. If given, then <em class='text-primary'>retail price</em> must be left blank.") if IS_PROVIDER\
    else _("Maximum retail price allowed by your provider.")


class ItemCategory(AbstractWatchModel):
    """
    Category of :class:`items.models.Product`. User must select the category from
    a list so, upon installation of the project some categories must be set.
    """
    UPLOAD_TO = 'item/categories'
    PLACE_HOLDER = 'no_photo.png'
    name = models.CharField(_("name"), max_length=100, unique=True,
                            help_text=_("Name of the category."))
    slug = models.SlugField(unique=True,
                            help_text=_("Slug of the category."))
    description = models.TextField(_("description"), blank=True,
                                   help_text=_("Description of the category."))
    badge_text = models.CharField(_("badge text"), max_length=25, blank=True,
                                  help_text=_("Text in the badge that appears on the category. "
                                              "<strong>E.g.:</strong> -20%, -30%, New, etc."))
    appear_in_menu = models.BooleanField(_("appear in menu"), default=False,
                                         help_text=_("Category will appear in main menu if checked."))
    is_active = models.BooleanField(verbose_name="Active ?", default=True,
                                    help_text=_("Make it visible or no."))
    order_of_appearance = models.IntegerField(default=1,
                                              help_text=_("Order of appearance in a list of categories."))
    previews_count = models.IntegerField(_("elements in preview"), default=PRODUCTS_PREVIEWS_PER_ROW,
                                         help_text=_("Number of elements in the category preview on home page. "
                                                     "Must be a multiple of 4."))
    items_count = models.IntegerField(default=0, editable=False,
                                      help_text="Number of items in this category.")
    image = MultiImageField(upload_to=UPLOAD_TO, blank=True, null=True, max_size=500)
    # A list of 366 integer values, each of which representing the number of items of this category
    # that were traded (sold or delivered) on a day out of the 366 previous (current day being the last)

    content_type = models.CharField(max_length=15, choices=SMART_CATEGORY_TYPE_CHOICES,blank=True, null=True,
                                    help_text=_("Whether it is a flat content or a menu preview."))
    items_traded_history = ListField()
    turnover_history = ListField()
    earnings_history = ListField()
    orders_count_history = ListField()

    # SUMMARY INFORMATION
    total_items_traded = models.IntegerField(default=0)
    total_turnover = models.IntegerField(default=0)
    total_earnings = models.IntegerField(default=0)
    total_orders_count = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = 'item categories'

    def __unicode__(self):
        return self.name

    def report_counters_to_umbrella(self):
        try:
            umbrella_obj = ItemCategory.objects.using(UMBRELLA).get(slug=self.slug)
        except:
            umbrella_obj = ItemCategory.objects.using(UMBRELLA).create(name=self.name, slug=self.slug)
        set_counters(umbrella_obj)
        increment_history_field(umbrella_obj, 'items_traded_history')
        increment_history_field(umbrella_obj, 'turnover_history')
        increment_history_field(umbrella_obj, 'orders_count_history')
        umbrella_obj.save(using=UMBRELLA)

    def delete(self, *args, **kwargs):
        try:
            os.unlink(self.image.path)
            os.unlink(self.image.small_path)
            os.unlink(self.image.thumb_path)
        except:
            pass
        from ikwen_webnode.web.models import Banner, SmartCategory
        for banner in Banner.objects.all():
            try:
                banner.items_fk_list.remove(self.id)
                banner.items_count = banner.get_category_queryset().count()
                banner.save()
            except ValueError:
                pass
        for smart_category in SmartCategory.objects.all():
            try:
                smart_category.items_fk_list.remove(self.id)
                smart_category.items_count = smart_category.get_category_queryset().count()
                smart_category.save()
            except ValueError:
                pass
        super(ItemCategory, self).delete(*args, **kwargs)

    def get_visible_items(self):
        item_queryset = self.get_visible_items()
        service_queryset = self.get_visible_recurring_payment_services()
        if item_queryset.count() > 0:
            return list(item_queryset)
        else:
            return list(service_queryset)

    def get_visible_items(self):
        return self.item_set.filter(visible=True, is_duplicate=False)

    def get_visible_recurring_payment_services(self):
        return self.recurringpaymentservice_set.filter(visible=True)

    def get_suited_previews_count(self):
        count = len(self.get_visible_items()) / PRODUCTS_PREVIEWS_PER_ROW
        return count * PRODUCTS_PREVIEWS_PER_ROW


class AbstractItem(AbstractWatchModel):
    """
    Base class for a :class:`Item` or :class:`RecurringPaymentService`
    offered by a :class:`profile.models.Provider` and retailed by other people.
    """
    provider = models.ForeignKey(Service, editable=IS_RETAILER, related_name='+')
    category = models.ForeignKey(ItemCategory)
    name = models.CharField(max_length=100, db_index=True,
                            help_text=_("Name of the item."))
    slug = models.SlugField(editable=False,
                            help_text=_("Slug of the item."))
    brand = models.CharField(max_length=60, db_index=True, blank=True, null=True,
                             help_text=_("Brand of the item."))
    summary = models.TextField(blank=True, null=True,
                               help_text=_("Summary of the item."))
    description = models.TextField(blank=True, null=True,
                                   help_text=_("Description of the item."))
    badge_text = models.CharField(max_length=25, blank=True, null=True,
                                  help_text=_("Text in the badge that appears on the item. "
                                              "<strong>E.g.:</strong> -20%, -30%, New, etc."))

    photos = ListField(EmbeddedModelField('Photo'), editable=False)
    # PRICES
    wholesale_price = models.FloatField(blank=IS_RETAILER, null=IS_RETAILER, help_text=wholesale_price_help_text, default=0)
    retail_price = models.FloatField(blank=True, null=True, help_text=retail_price_help_text)
    max_price = models.FloatField(blank=True, null=True, help_text=max_price_help_text)

    # SALE INFORMATION: They are automatically set whenever retail_price is updated
    on_sale = models.BooleanField(default=False, editable=False,
                                  help_text="Whether or not this item is on sale.")
    previous_price = models.IntegerField(blank=True, null=True, editable=False,
                                         help_text="Previous retail price when retail_price is updated.")

    total_rating = models.IntegerField(default=0, blank=True, null=True,
                                       help_text="The sum of all rating ever given.")
    rating_count = models.IntegerField(default=0, blank=True, null=True,
                                       help_text="The number of times item was rated.")

    # TODO: Deal with information below to manage wholesale purchases in next version
    # WHOLESALE INFORMATION
    # self_sale_price = models.FloatField(blank=True, null=True,
    #                                help_text=_("Retail price at which the provider sells on his own website."))
    # measurement = models.CharField(max_length=30, blank=True,
    #                                help_text=_("Unit of measurement to sell this item in wholesale. Eg: crate"))
    # measurement_units_equivalent = models.IntegerField(blank=True, null=True,
    #                                                    help_text=_("Number of units contained in one measurement."
    #                                                                "Eg: 1 crate=12 bottles, so input 12."))
    # measurement_unit_price = models.IntegerField(blank=True, null=True,
    #                                              help_text=_("Price of a unit of measurement of this item."))
    # min_quantity = models.IntegerField(default=1,
    #                                    help_text=_("Minimum number of units of measurement to purchase in wholesale."))

    # Accessibility information
    visible = models.BooleanField(default=True)
    tags = models.CharField(max_length=255, db_index=True, blank=True, editable=False)
    in_trash = models.BooleanField(default=False, editable=False)
    is_retailed = models.BooleanField(default=False, editable=False)  # If True, prices cannot be modified by Provider

    # A list of 366 integer values, each of which representing the number of units
    # of this item sold on a day of the 366 previous (current day being the last)
    units_sold_history = ListField()

    total_units_sold = models.IntegerField(default=0,
                                           help_text="Number of units sold since online.")

    class Meta:
        abstract = True

    def __unicode__(self):
        return self.name

    def _get_image(self):
        return self.photos[0].image if len(self.photos) > 0 else None
    image = property(_get_image)

    def get_photos_url_list(self):
        photo_list = []
        for photo in self.photos:
            photo_list.append({
                'original': photo.image.url,
                'small': photo.image.small_url,
                'thumb': photo.image.thumb_url
            })
        return photo_list

    def get_photos_ids_list(self):
        return ','.join([photo.id for photo in self.photos])

    def get_rating(self):
        if self.rating_count:
            return self.total_rating / self.rating_count
        return 0

    def delete(self, *args, **kwargs):
        for photo in self.photos:
            photo.delete(*args, **kwargs)
        from ikwen_webnode.web.models import Banner, SmartCategory
        for banner in Banner.objects.all():
            try:
                banner.items_fk_list.remove(self.id)
                banner.items_count = banner.get_item_queryset().count()
                banner.save()
            except ValueError:
                pass
        for smart_category in SmartCategory.objects.all():
            try:
                smart_category.items_fk_list.remove(self.id)
                smart_category.items_count = smart_category.get_item_queryset().count()
                smart_category.save()
            except ValueError:
                pass
        for obj in ItemCategory.objects.all():
            obj.items_count = obj.item_set.filter(in_trash=False).count()
            obj.save()
        super(AbstractItem, self).delete(*args, **kwargs)

    def to_dict(self):
        var = to_dict(self)
        var['image'] = self.image.url if self.image and self.image.name else ''
        var['url'] = reverse('items:change_item', args=(self.id, ))
        del(var['units_sold_history'])
        del(var['tags'])
        return var


class Item(AbstractItem):
    size = models.CharField(max_length=30, blank=True, null=True,
                            help_text=_("Size in custom unit of measurement for this item."))
    # TODO: Manage colors the smooth way
    color = models.CharField(max_length=30, blank=True, null=True,
                             help_text=_("Color of item as hexadecimal code."))
    weight = models.CharField(max_length=30, blank=True, null=True,
                              help_text=_("Weight in grams."))
    stock = models.IntegerField(blank=True, null=True,
                                help_text=_("Stock of the item."))
    unit_of_measurement = models.CharField(max_length=60, blank=True, null=True,
                                           help_text=_("Unit of measurement for this item."))
    min_order = models.IntegerField(default=1,
                                    help_text=_("Minimum number of units one can order. Excellent for wholesale."))

    video_url = models.URLField(blank=True, null=True,
                                    help_text=_("Link of the video talking about the item."))
    batch_upload = models.ForeignKey('BatchUpload', blank=True, null=True, editable=False)

    # Django ORM does not support .distinct() with MongoDB Backend.
    # This field helps track which objects are duplicates of another
    # The field is set upon the saving and deleting an object using
    # :func:`items.utils.mark_duplicates`
    is_duplicate = models.BooleanField(default=False, editable=False)
    has_background_image = models.BooleanField(default=False,
                                    help_text=_("Specify if you want the item to be presented as background banner or just as an image"))

    class Meta:
        permissions = (
            ("ik_manage_item", _("Manage items")),
        )

    def delete(self, *args, **kwargs):
        super(Item, self).delete(*args, **kwargs)
        from ikwen_kakocase.kako.utils import mark_duplicates
        mark_duplicates(self)

    def get_size_list(self):
        """
        Grabs sizes for item of the same category having the same slug
        """
        size_list = set([p.size for p in Item.objects.filter(category=self.category, brand=self.brand,
                                                                slug=self.slug, stock__gt=0).order_by('id')
                         if p.size])
        size_list_obj = []

        from ikwen_kakocase.sales.views import apply_promotion_discount
        for size in size_list:
            try:
                obj = Item.objects.filter(category=self.category, brand=self.brand, slug=self.slug, size=size)[0]
                obj = apply_promotion_discount([obj])[0]

                size_list_obj.append({'label': obj.size, 'stock': obj.stock, 'retail_price': obj.retail_price,
                                      'id': obj.pk, 'wholesale_price': obj.wholesale_price, 'max_price': obj.max_price})
            except:
                pass
        return size_list_obj

    def get_size_list_label(self):
        """
        A string version of get_size_list suited for display
        """
        return ' / '.join([obj['label'] for obj in self.get_size_list()])

    # def get_color_list(self):
    #     """
    #     Grabs colors for item of the same category having the same slug and same size
    #     """
    #     return list(set([p.color for p in Item.objects.filter(category=self.category, brand=self.brand, size=self.size,
    #                                                              slug=self.slug, stock__gte=0).order_by('id')
    #                      if p.color]))


class RecurringPaymentService(AbstractItem):
    """
    Service an end user may subscribe to through the :class:`people.models.Retailer`

    :attr:duration duration in number of days that the payment covers
    :attr:duration_text Equivalent of the duration suitable for display
    """
    duration = models.IntegerField()
    duration_text = models.CharField(max_length=30)


class Photo(models.Model):
    UPLOAD_TO = 'items/photos'
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


class BatchUpload(models.Model):
    UPLOAD_TO = 'items/batch_uploads'
    spreadsheet = models.FileField(upload_to=UPLOAD_TO)

    def delete(self, *args, **kwargs):
        os.unlink(self.spreadsheet.path)
        super(BatchUpload, self).delete(*args, **kwargs)

    def __unicode__(self):
        return self.spreadsheet


def update_category_items_count(sender, **kwargs):
    """
    Receiver of the post_save signals of Item.
    It resets the ItemCategory.items_count accordingly
    """
    if sender != Item:  # Avoid unending recursive call
        return
    for obj in ItemCategory.objects.all():
        obj.items_count = obj.item_set.filter(in_trash=False).count()
        obj.save()


def update_item_containers_items_count(sender, **kwargs):
    """
    Receiver of the post_delete signals of Item. It resets the 
    ItemCategory.items_count and SmartCategory.items_fk_list accordingly
    """
    if sender != Item:  # Avoid unending recursive call
        return
    for obj in ItemCategory.objects.all():
        obj.items_count = obj.item_set.filter(in_trash=False).count()
        obj.save()
    instance = kwargs['instance']
    from ikwen_webnode.web.models import Banner, SmartCategory
    for obj in Banner.objects.all():
        if instance.id in obj.items_fk_list:
            obj.items_fk_list.remove(instance.id)
        obj.items_count = len(obj.items_fk_list)
        obj.save()
    for obj in SmartCategory.objects.all():
        if instance.id in obj.items_fk_list:
            obj.items_fk_list.remove(instance.id)
        obj.items_count = len(obj.items_fk_list)
        obj.save()

post_save.connect(update_category_items_count, dispatch_uid="item_post_save_id")
post_delete.connect(update_item_containers_items_count, dispatch_uid="item_post_delete_id")
