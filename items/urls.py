
from django.conf.urls import patterns, url
from django.contrib.auth.decorators import permission_required

from ikwen_webnode.items.provider.views import do_import_items_from_spreadsheet, item_batch_uploader, set_stock
from ikwen_webnode.items.views import ProviderList, ProviderItemList, do_import_items, \
    update_item_retail_price, get_menu_for_category, \
    item_photo_uploader, ChangeItem, ItemList, put_item_in_trash, \
    ProviderItemDetail, update_item_stock, delete_photo, CategoryList, ChangeCategory, delete_category, \
    toggle_category_attribute, load_item_from_url, save_item_from_url

urlpatterns = patterns(
    '',
    url(r'^providers/$', ProviderList.as_view(), name='provider_list'),
    url(r'^items/(?P<provider_id>[-\w]+)/$', ProviderItemList.as_view(), name='provider_item_list'),
    url(r'^detail/(?P<provider_id>[-\w]+)/(?P<item_id>[-\w]+)/$',
        permission_required('items.ik_manage_item')(ProviderItemDetail.as_view()), name='provider_item_detail'),
    url(r'^do_import_items$', do_import_items, name='do_import_items'),
    url(r'^update_item_retail_price$', update_item_retail_price, name='update_item_retail_price'),
    url(r'^toggle_category_attribute$', toggle_category_attribute, name='toggle_category_attribute'),
    url(r'^update_item_stock$', update_item_stock, name='update_item_stock'),
    url(r'^item_photo_uploader$', item_photo_uploader, name='item_photo_uploader'),
    url(r'^delete_photo$', delete_photo, name='delete_photo'),
    url(r'^item/$', permission_required('items.ik_manage_item')(ChangeItem.as_view()), name='change_item'),
    url(r'^item/(?P<item_id>[-\w]+)/$', permission_required('items.ik_manage_item')(ChangeItem.as_view()),
        name='change_item'),
    url(r'^categories/$', permission_required('items.ik_manage_item')(CategoryList.as_view()), name='category_list'),
    url(r'^category/$', permission_required('items.ik_manage_item')(ChangeCategory.as_view()),
        name='change_category'),
    url(r'^category/(?P<category_id>[-\w]+)/$', permission_required('items.ik_manage_item')(ChangeCategory.as_view()),
        name='change_category'),
    url(r'^delete_category$', delete_category, name='delete_category'),
    url(r'^items/$', permission_required('items.ik_manage_item')(ItemList.as_view()), name='item_list'),

    url(r'^item_batch_uploader$', item_batch_uploader, name='item_batch_uploader'),
    url(r'^do_import_items_from_spreadsheet$', do_import_items_from_spreadsheet, name='do_import_items_from_spreadsheet'),
    url(r'^put_item_in_trash$', put_item_in_trash, name='put_item_in_trash'),
    url(r'^load_item_from_url$', load_item_from_url, name='load_item_from_url'),
    url(r'^save_item_from_url$', save_item_from_url, name='save_item_from_url'),
    url(r'^get_menu_for_category$', get_menu_for_category, name='get_menu_for_category'),

    url(r'^api/set_stock/(?P<api_signature>[-\w]+)/(?P<ref>[-\w]+)/(?P<units>\d+(.\d)*)/$', set_stock, name='set_stock')
)
