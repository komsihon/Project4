import os

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save
from django.template import Context
from django.template.loader import get_template
from django.utils.module_loading import import_by_path
from djangotoolbox.fields import ListField
from ikwen.core.fields import MultiImageField

from ikwen.core.models import Model, Module
from ikwen_kakocase.kako.models import Product
from django.utils.translation import gettext_lazy as _

from ikwen_kakocase.kakocase.models import ProductCategory

FLAT = "Flat"
MENU = "Menu"

HOME_SECTION_TYPE_CHOICES = (
    (FLAT, _("Flat")),
    (MENU, _("Menu"))
)

FLAT_PAGE = "FlatPage"
ITEM_LIST = "ItemList"
MODULE = "Module"
SMART_CATEGORY_TYPE_CHOICES = (
    (FLAT_PAGE, _("Flat Page")),
    (ITEM_LIST, _("Item List"))
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
                             help_text=_("Title that appears in the site menu bar."))
    slug = models.SlugField(unique=True)
    order_of_appearance = models.IntegerField(default=1,
                                              help_text=_("Order of appearance of the section. Same order of "
                                                          "appearance will result in an ordering in alphabetical order"))
    items_count = models.IntegerField(default=0,
                                      help_text="Number of products in this category.")
    items_fk_list = ListField()
    is_active = models.BooleanField(verbose_name="Active ?", default=True,
                                    help_text=_("Make it visible or no."))

    class Meta:
        abstract = True
        ordering = ('-id', 'slug', )

    def get_category_queryset(self):
        return ProductCategory.objects.filter(pk__in=self.items_fk_list)

    def get_product_queryset(self):
        return Product.objects.exclude(Q(retail_price__isnull=True) & Q(retail_price=0))\
            .filter(pk__in=self.items_fk_list, visible=True, is_duplicate=False)

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

    content_type = models.CharField(max_length=15, choices=HOME_SECTION_TYPE_CHOICES,
                                    help_text=_("Whether it is a flat content or a menu preview."))
    image = MultiImageField(upload_to=UPLOAD_TO, blank=True, null=True, max_size=1920)
    background_image = models.BooleanField(default=False,
                                           help_text="Check to make the image cover the "
                                                     "background of this section")
    description = models.TextField(blank=True,
                                   help_text="Text in the section")
    text_position = models.CharField(max_length=10, default=RIGHT, choices=TEXT_POSITIONS)
    cta = models.CharField(verbose_name=_("Call To Action"), max_length=30, blank=True,
                           help_text=_('Action you want your visitors to undertake. '
                                       '<em><strong>E.g:</strong> "Join Us Now"</em>'))
    target_url = models.URLField(blank=True)

    class Meta:
        ordering = ('order_of_appearance', '-id', )
        permissions = (
            ("ik_manage_marketing", _("Manage marketing tools")),
        )

    def __unicode__(self):
        return self.title

    def render(self, request=None):
        if self.content_type == FLAT:
            c = Context({'section': self})
            html_template = get_template('webnode/snippets/homepage_section_flat.html')
            return html_template.render(c)
        else:  # The section points to a Menu
            try:
                # The actual menu points to an Item List
                smart_category = SmartCategory.objects.get(slug=self.description)
                category_list = list(smart_category.get_category_queryset())
                # product_list = ....
                c = Context({'item_list': smart_category.get_product_queryset()})
                html_template = get_template('webnode/snippets/homepage_section_item_list.html')
                return html_template.render(c)
            except SmartCategory.DoesNotExist:
                # The actual menu points to a Module
                mod = Module.objects.get(slug=self.description)
                renderer = import_by_path(mod.homepage_section_renderer)
                return renderer(self, request)


class SmartCategory(SmartObject):
    UPLOAD_TO = 'commarketing/smart_categories'

    content_type = models.CharField(max_length=15, choices=SMART_CATEGORY_TYPE_CHOICES,
                                    help_text=_("Whether this menu points to a page or a list of items."))
    image = MultiImageField(upload_to=UPLOAD_TO, blank=True, null=True, max_size=500)
    description = models.TextField(blank=True,
                                   help_text=_("Description of the category."))
    badge_text = models.CharField(max_length=25, blank=True,
                                  help_text=_("Text in the badge that appears on the smart category. "
                                              "<strong>E.g.:</strong> -20%, -30%, New, etc."))
    appear_in_menu = models.BooleanField(default=False,
                                         help_text=_("Smart Category will appear in main menu if checked."))

    def _get_module(self):
        try:
            return Module.objects.get(slug=self.slug)
        except:
            pass
    module = property(_get_module)


def sync_module_menu(sender, **kwargs):
    """
    Creates or delete the corresponding menu
    whenever you activate/deactivate the module
    """
    if sender != Module:  # Avoid unending recursive call
        return
    module = kwargs['instance']
    if module.is_active:
        try:
            menu = SmartCategory.objects.get(slug=module.slug)
            menu.title = module.title
            menu.image = module.image
            menu.save()
        except SmartCategory.DoesNotExist:
            order_of_appearance = SmartCategory.objects.filter(is_active=True).count()
            if module.url_name:  # Only Modules with URL generate a menu
                SmartCategory.objects.create(title=module.title, slug=module.slug, content_type=MODULE,
                                             order_of_appearance=order_of_appearance, image=module.image,
                                             appear_in_menu=True)
    else:
        SmartCategory.objects.filter(slug=module.slug).delete()
        HomepageSection.objects.filter(description=module.slug).delete()

post_save.connect(sync_module_menu, dispatch_uid="module_post_save_id")
