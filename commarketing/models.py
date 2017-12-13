import os

from django.conf import settings
from django.db import models
from django.db.models import Q
from djangotoolbox.fields import ListField
from ikwen.core.fields import MultiImageField

from ikwen.core.models import Model
from ikwen_kakocase.kako.models import Product, RecurringPaymentService
from django.utils.translation import gettext_lazy as _

from ikwen_kakocase.kakocase.models import ProductCategory, CATEGORIES_PREVIEWS_PER_ROW, PRODUCTS_PREVIEWS_PER_ROW

CATEGORIES = "Categories"
PRODUCTS = "Products"
SERVICES = "Services"

CONTENT_TYPE_CHOICES = (
    (CATEGORIES, _("Categories")),
    (PRODUCTS, _("Products")),
    (SERVICES, _("Services"))
)

SLIDE = 'Slide'
TILES = 'Tiles'
POPUP = 'Popup'
FULL_WIDTH_SECTION = 'FullWidthSection'
FULL_SCREEN_POPUP = 'FullScreenPopup'

if getattr(settings, 'TEMPLATE_WITH_HOME_TILES', False):
    DISPLAY_CHOICES = (
        # (DEFAULT, _("Default")),
        (SLIDE, _("Slide")),
        (TILES, _("Tiles")),
        (POPUP, _("Popup")),
        (FULL_WIDTH_SECTION, _("Full-width section")),
        (FULL_SCREEN_POPUP, _("Full screen popup"))
    )
else:
    DISPLAY_CHOICES = (
        # (DEFAULT, _("Default")),
        (SLIDE, _("Slide")),
        (POPUP, _("Popup")),
        (FULL_WIDTH_SECTION, _("Full-width section")),
        (FULL_SCREEN_POPUP, _("Full screen popup"))
    )


class SmartObject(Model):
    title = models.CharField(max_length=60,
                             help_text=_("Smart commercial title."))
    slug = models.SlugField(unique=True)
    order_of_appearance = models.IntegerField(default=1,
                                              help_text=_("Order of appearance of the section. Same order of "
                                                          "appearance will result in an ordering in alphabetical order"))
    content_type = models.CharField(max_length=15, choices=CONTENT_TYPE_CHOICES,
                                    help_text=_("Whether it is a list of categories or a list of products"))
    items_count = models.IntegerField(default=0,
                                      help_text="Number of products in this category.")
    items_fk_list = ListField()
    is_active = models.BooleanField(verbose_name="Active ?", default=True,
                                    help_text=_("Make it visible or no."))

    class Meta:
        abstract = True
        ordering = ('-id', 'slug', )

    def get_category_queryset(self):
        if self.content_type == CATEGORIES:
            return ProductCategory.objects.filter(pk__in=self.items_fk_list)

    def get_product_queryset(self):
        if self.content_type == PRODUCTS:
            return Product.objects.exclude(Q(retail_price__isnull=True) & Q(retail_price=0))\
                .filter(pk__in=self.items_fk_list, visible=True, is_duplicate=False)
        elif self.content_type == SERVICES:
            return RecurringPaymentService.objects.filter(pk__in=self.items_fk_list, visible=True, is_duplicate=False)

    def get_suited_previews_count(self):
        if self.content_type == CATEGORIES:
            count = self.get_category_queryset().count() / CATEGORIES_PREVIEWS_PER_ROW
            return count * CATEGORIES_PREVIEWS_PER_ROW
        count = self.get_product_queryset().count() / PRODUCTS_PREVIEWS_PER_ROW
        return count * PRODUCTS_PREVIEWS_PER_ROW

    def delete(self, *args, **kwargs):
        try:
            os.unlink(self.image.path)
            os.unlink(self.image.small_path)
            os.unlink(self.image.thumb_path)
        except:
            pass
        super(SmartObject, self).delete(*args, **kwargs)


class Banner(SmartObject):
    """
    Any of banners owner of the site may use as Slide, Popup, etc
    to market some products on the site.
    """
    UPLOAD_TO = 'commarketing/banners'

    image = MultiImageField(upload_to=UPLOAD_TO, blank=True, null=True, max_size=1920)
    display = models.CharField(max_length=30, choices=DISPLAY_CHOICES, default=SLIDE,
                               help_text="How the image is shown on the site. Can be one of "
                                         "<strong>Slide, Popup, FullWidthSection</strong> "
                                         "or <strong>FullScreenPopup</strong>")
    # location = models.CharField(max_length=60, blank=True,
    #                             help_text="Bloc of the page where banner should appear. "
    #                                       "Applies to Default banners only.")
    cta = models.CharField(verbose_name=_("Call To Action"), max_length=30, blank=True,
                           help_text=_('Action you want you visitors to undertake. '
                                       '<em><strong>E.g:</strong> "Buy Now"</em>'))
    target_url = models.URLField(blank=True)

    class Meta:
        unique_together = ('slug', 'display', )
        ordering = ('-id', 'slug', )
        permissions = (
            ("ik_manage_marketing", _("Manage marketing tools")),
        )


class HomepageSection(SmartObject):
    """
    Any full-width section on the homepage
    """
    UPLOAD_TO = 'commarketing/homepage_sections'
    LEFT = "Left"
    RIGHT = "Right"
    CENTER = "Center"

    TEXT_POSITIONS = (
        (LEFT, _("Left")),
        (CENTER, _("Center")),
        (RIGHT, _("Right"))
    )

    image = MultiImageField(upload_to=UPLOAD_TO, blank=True, null=True, max_size=1920)
    background_image = models.BooleanField(default=False,
                                           help_text="Check to make the image cover the "
                                                     "background of this section")
    description = models.TextField(blank=True,
                                   help_text="Text in the section")
    text_position = models.CharField(max_length=10, default=RIGHT, choices=TEXT_POSITIONS)
    cta = models.CharField(verbose_name=_("Call To Action"), max_length=30, blank=True,
                           help_text=_('Action you want your visitors to undertake. '
                                       '<em><strong>E.g:</strong> "Buy Now"</em>'))
    target_url = models.URLField(blank=True)

    class Meta:
        ordering = ('order_of_appearance', '-id', )
        permissions = (
            ("ik_manage_marketing", _("Manage marketing tools")),
        )


class SmartCategory(SmartObject):
    UPLOAD_TO = 'commarketing/smart_categories'

    image = MultiImageField(upload_to=UPLOAD_TO, blank=True, null=True, max_size=500)
    description = models.TextField(blank=True,
                                   help_text=_("Description of the category."))
    badge_text = models.CharField(max_length=25, blank=True,
                                  help_text=_("Text in the badge that appears on the smart category. "
                                              "<strong>E.g.:</strong> -20%, -30%, New, etc."))
    appear_in_menu = models.BooleanField(default=False,
                                         help_text=_("Smart Category will appear in main menu if checked."))


# ########   BELOW APPLY TO PROVIDER    ######### #

class Push(Model):
    """
    A push made by a Provider to spotlight a product so that Retailers promote
    it on their websites. Any newly made Push results in a notification that appear
    on ikwen console of all Retailers of the actual Provider
    """
    product = models.ForeignKey(Product)
    about = models.TextField()

    class Meta:
        ordering = ('-id', )
