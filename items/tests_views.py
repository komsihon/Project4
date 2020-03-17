import json

from django.conf import settings
from django.core.management import call_command
from django.core.urlresolvers import reverse
from django.test.client import Client
from django.test.utils import override_settings
from django.utils import unittest
from ikwen_webnode.web.models import SmartCategory

from ikwen.accesscontrol.backends import UMBRELLA
from ikwen.accesscontrol.models import Member
from ikwen.core.models import Service, ConsoleEvent
from ikwen.core.utils import get_service_instance, add_database_to_settings
from ikwen_webnode.items.models import Item, ItemCategory, RecurringPaymentService
from ikwen_webnode.webnode.models import OperatorProfile


def wipe_test_data(db='default'):
    """
    This test was originally built with django-nonrel 1.6 which had an error when flushing the database after
    each test. So the flush is performed manually with this custom tearDown()
    """
    import ikwen_webnode.items.models
    import ikwen_webnode.web.models
    import ikwen.core.models
    if db != 'default':
        add_database_to_settings(db)
    for name in ('Item','ItemCategory', 'RecurringPaymentService', 'Photo'):
        model = getattr(ikwen_webnode.items.models, name)
        model.objects.using(db).all().delete()
    for name in ('Banner', 'SmartCategory'):
        model = getattr(ikwen_webnode.web.models, name)
        model.objects.using(db).all().delete()
    for name in ('Application', 'Service', 'Config', 'ConsoleEventType', 'ConsoleEvent', 'Country', ):
        model = getattr(ikwen.core.models, name)
        model.objects.using(db).all().delete()


def copy_service_and_config_to_default_db():
    service = get_service_instance(using=UMBRELLA)
    service.save(using='default')  # Copies Service to the default DB
    config = OperatorProfile.objects.using(UMBRELLA).get(service=service)
    config.save(using='default')
    return service, config


class KakoViewsTestCase(unittest.TestCase):
    """
    This test derives django.utils.unittest.TestCate rather than the default django.test.TestCase.
    Thus, self.client is not automatically created and fixtures not automatically loaded. This
    will be achieved manually by a custom implementation of setUp()
    """
    fixtures = ['wn_members.yaml', 'wn_profiles.yaml', 'categories.yaml', 'orders.yaml']

    def setUp(self):
        self.client = Client()
        call_command('loaddata', 'wn_setup_data.yaml', database=UMBRELLA)
        call_command('loaddata', 'wn_operators_configs.yaml', database=UMBRELLA)
        for fixture in self.fixtures:
            call_command('loaddata', fixture)

    def tearDown(self):
        wipe_test_data()
        wipe_test_data('test_kc_tecnomobile')
        wipe_test_data(UMBRELLA)

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_ProviderListView(self):
        """
        Page must return HTTP 200 status
        Providers with 'Auto' last_stock_update_method must come first
        """
        copy_service_and_config_to_default_db()
        response = self.client.get(reverse('items:provider_list'))
        self.assertEqual(response.status_code, 200)
        providers = response.context['providers']
        self.assertEqual(providers.count(), 2)
        self.assertEqual(providers[0].service.project_name, 'sabc')

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_ProviderListView_json_format(self):
        """
        Requesting providers list with GET parameter format=json&q=searchTerm should
        perform a search and return a list providers in JSON format.
        """
        copy_service_and_config_to_default_db()
        response = self.client.get(reverse('items:provider_list'), {'format': 'json', 'q': 'mobil', 'start': 0, 'length': 24})
        self.assertEqual(response.status_code, 200)
        # print response.content
        providers = json.loads(response.content)
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0]['company_name'], 'Tecno Mobile Telecom')

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_ProviderListView_query_by_category_json_format(self):
        """
        Requesting providers list with GET parameter format=json&category_slug=categorySlug&q=searchTerm should
        perform a search and return a list providers in JSON format.
        """
        copy_service_and_config_to_default_db()
        response = self.client.get(reverse('items:provider_list'),
                                   {'format': 'json', 'category_slug': 'beverage', 'q': 'bra', 'start': 0, 'length': 24})
        self.assertEqual(response.status_code, 200)
        providers = json.loads(response.content)
        self.assertEqual(len(providers), 1)
        self.assertEqual(providers[0]['company_name'], 'Les Brasseries du Cameroun')

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_ProviderItemListView(self):
        """
        Page must return HTTP 200 status, items with largest items_sold must come first.
        """
        copy_service_and_config_to_default_db()
        service = Service.objects.using(UMBRELLA).get(pk='56eb6d04b37b3379b531b102')
        add_database_to_settings(service.database)
        Item.objects.using(service.database).all().delete()
        call_command('loaddata', 'wn_setup_data.yaml', database=service.database)
        call_command('loaddata', 'items.yaml', database=service.database)
        provider = Service.objects.using(service.database).get(pk='56eb6d04b37b3379b531b102')
        Item.objects.using(service.database).exclude(provider=provider).delete()
        response = self.client.get(reverse('items:provider_item_list', args=('56922874b37b33706b51f002', )))
        self.assertEqual(response.status_code, 200)
        items = response.context['items']
        self.assertEqual(items.count(), 2)
        self.assertEqual(items[0].name, 'Mutzig')
        from pymongo import Connection
        cnx = Connection()
        cnx.drop_database(service.database)

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_ProviderItemListView_json_format(self):
        """
        Requesting items list with GET parameter format=json&q=searchTerm should.
        Result must return as a list of JSON objects
        """
        copy_service_and_config_to_default_db()
        service = Service.objects.using(UMBRELLA).get(pk='56eb6d04b37b3379b531b102')
        add_database_to_settings(service.database)
        Item.objects.using(service.database).all().delete()
        call_command('loaddata', 'items.yaml', database=service.database)
        response = self.client.get(reverse('items:provider_item_list', args=('56922874b37b33706b51f002', )),
                                   {'format': 'json', 'q': 'col', 'start': 0, 'length': 24})
        self.assertEqual(response.status_code, 200)
        items = json.loads(response.content)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['name'], 'Coca-Cola')
        from pymongo import Connection
        cnx = Connection()
        cnx.drop_database(service.database)

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_ProviderItemListView_query_by_category_json_format(self):
        """
        Requesting items list with GET parameter format=json&category_slug=slug&q=searchTerm should.
        Result must return as a list of JSON objects
        """
        copy_service_and_config_to_default_db()
        service = Service.objects.using(UMBRELLA).get(pk='56eb6d04b37b3379b531b102')
        add_database_to_settings(service.database)
        Item.objects.using(service.database).all().delete()
        call_command('loaddata', 'wn_setup_data.yaml', database=service.database)
        call_command('loaddata', 'items.yaml', database=service.database)
        provider = Service.objects.using(service.database).get(pk='56eb6d04b37b3379b531b102')
        Item.objects.using(service.database).exclude(provider=provider).delete()
        response = self.client.get(reverse('items:provider_item_list', args=('56922874b37b33706b51f002', )),
                                   {'format': 'json', 'category_slug': 'food', 'q': 'col', 'start': 0, 'length': 24})
        self.assertEqual(response.status_code, 200)
        items = json.loads(response.content)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['name'], 'Coca-Cola')
        from pymongo import Connection
        cnx = Connection()
        cnx.drop_database(service.database)

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_ItemList(self):
        """
        Page must return HTTP 200 status, items with largest items_sold must come first.
        """
        call_command('loaddata', 'wn_setup_data.yaml')
        call_command('loaddata', 'wn_operators_configs.yaml')
        call_command('loaddata', 'items.yaml')
        self.client.login(username='member3', password='admin')
        response = self.client.get(reverse('items:item_list'))
        self.assertEqual(response.status_code, 200)
        items = response.context['item_list']
        self.assertEqual(items.count(), 3)
        self.assertEqual(items[0].name, 'Mutzig')

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_ItemList_json_format(self):
        """
        Requesting items list with GET parameter format=json&q=searchTerm should.
        Result must return as a list of JSON objects
        """
        copy_service_and_config_to_default_db()
        call_command('loaddata', 'items.yaml')
        self.client.login(username='member3', password='admin')
        response = self.client.get(reverse('items:item_list'),
                                   {'format': 'json', 'q': 'col', 'start': 0, 'length': 24})
        self.assertEqual(response.status_code, 200)
        items = json.loads(response.content)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['name'], 'Coca-Cola')

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_ItemList_filter_by_category_json_format(self):
        """
        Requesting items list with GET parameter format=json&q=searchTerm should.
        Result must return as a list of JSON objects
        """
        copy_service_and_config_to_default_db()
        call_command('loaddata', 'items.yaml')
        self.client.login(username='member3', password='admin')
        response = self.client.get(reverse('items:item_list'),
                                   {'format': 'json', 'category_slug': 'food', 'start': 0, 'length': 24})
        self.assertEqual(response.status_code, 200)
        items = json.loads(response.content)
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]['name'], 'Mutzig')

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_do_import_items(self):
        """
        Importing items merely copies a list of items from the provider database to the retailer database.
        Retailer profile and Member object are copied to the provider's database and vice versa.
        Every imported item must have the field is_retailed=True.
        """
        call_command('loaddata', 'wn_members.yaml', database=UMBRELLA)
        copy_service_and_config_to_default_db()
        service = Service.objects.using(UMBRELLA).get(pk='56eb6d04b37b3379b531b102')
        add_database_to_settings(service.database)
        Item.objects.using(service.database).all().delete()
        call_command('loaddata', 'wn_profiles.yaml', database=service.database)
        call_command('loaddata', 'items.yaml', database=service.database)
        self.client.login(username='member3', password='admin')
        response = self.client.get(reverse('items:do_import_items'),
                                   {'provider_slug': 'les-brasseries-du-cameroun',
                                    'provider_id': '56922874b37b33706b51f002',
                                    'item_ids': '55d1fa8feb60008099bd4152,55d1fa8feb60008099bd4153'})
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(response['success'])
        self.assertEqual(Item.objects.using('default').all().count(), 2)
        Member.objects.using(service.database).get(username='member3')  # Member must be in Provider's database
        OperatorProfile.objects.using(service.database).get(pk='56922874b37b33706b51f003')  # Retailer must be in Provider's database
        Service.objects.using(service.database).get(pk='56eb6d04b37b3379b531b103')  # Service must be in Provider's database
        for item in Item.objects.using(service.database).filter(pk__in=['55d1fa8feb60008099bd4152', '55d1fa8feb60008099bd4153']):
            self.assertTrue(item.is_retailed)
        from pymongo import Connection
        cnx = Connection()
        cnx.drop_database(service.database)

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_do_import_items_with_unauthorized_member(self):
        """
        Unauthorized member cannot import item
        """
        copy_service_and_config_to_default_db()
        response = self.client.get(reverse('items:do_import_items'))
        self.assertEqual(response.status_code, 302)

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_update_item_retail_price_with_modification_allowed(self):
        """
        Updating retail price works only when modification is allowed
        """
        copy_service_and_config_to_default_db()
        call_command('loaddata', 'wn_members.yaml', database=UMBRELLA)
        call_command('loaddata', 'items.yaml')
        self.client.login(username='member3', password='admin')
        response = self.client.get(reverse('items:update_item_retail_price'),
                                   {'item_id': '55d1fa8feb60008099bd4152', 'price': '500'})
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(response['success'])
        self.assertEqual(Item.objects.get(pk='55d1fa8feb60008099bd4152').retail_price, 500)

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_update_item_retail_price_with_new_price_bigger_than_max_price(self):
        """
        Retail price is set to max_price if new price is bigger than the max_price set by provider.
        """
        copy_service_and_config_to_default_db()
        call_command('loaddata', 'wn_members.yaml', database=UMBRELLA)
        call_command('loaddata', 'items.yaml')
        self.client.login(username='member3', password='admin')
        response = self.client.get(reverse('items:update_item_retail_price'),
                                   {'item_id': '55d1fa8feb60008099bd4152', 'price': '600'})
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(response['success'])
        self.assertEqual(Item.objects.get(pk='55d1fa8feb60008099bd4152').retail_price, 500)

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_update_item_retail_price_with_modification_not_allowed(self):
        """
        Updating retail price works only when modification is allowed
        """
        copy_service_and_config_to_default_db()
        call_command('loaddata', 'items.yaml')
        item = Item.objects.get(pk='55d1fa8feb60008099bd4152')
        item.retail_price_is_modifiable = False
        item.save()
        self.client.login(username='member3', password='admin')
        response = self.client.get(reverse('items:update_item_retail_price'),
                                   {'item_id': '55d1fa8feb60008099bd4152', 'price': '500'})
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.content)
        self.assertTrue(response['success'])
        self.assertEqual(item.retail_price, 450)


    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_AddItemView(self):
        """
        AddItemView must return HTTP 200 with or without a item, and return HTTP 302 if user unauthorized
        """
        call_command('loaddata', 'wn_members.yaml', database=UMBRELLA)
        call_command('loaddata', 'wn_setup_data.yaml')
        call_command('loaddata', 'wn_operators_configs.yaml')
        call_command('loaddata', 'items.yaml')
        copy_service_and_config_to_default_db()
        response = self.client.get(reverse('items:change_item'))
        self.assertEqual(response.status_code, 302)
        self.client.login(username='member3', password='admin')
        response = self.client.get(reverse('items:change_item'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('items:change_item'), {'item_id': '55d1fa8feb60008099bd4152'})
        self.assertEqual(response.status_code, 200)

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_submit_item_with_new_item(self):
        """
        submit_item view updates item information if it previously exists.
        Only retail_price can be set if user is a Retailer
        """
        copy_service_and_config_to_default_db()
        call_command('loaddata', 'wn_members.yaml', database=UMBRELLA)
        self.client.login(username='member3', password='admin')
        response = self.client.post(reverse('items:change_item'),
                                    {'name': 'New Black Chocolate', 'brand': 'Mambo',
                                     'category': '569228a9b37b3301e0706b51',
                                     'wholesale_price': '0',
                                     'retail_price': '600',
                                     'min_order': '1',
                                     'summary': 'Some summary',
                                     'description': 'Some description'})
        item = Item.objects.get(slug='new-black-chocolate')  # Slug must be correctly set
        self.assertEqual(item.name, 'New Black Chocolate')
        self.assertEqual(item.category, ItemCategory.objects.get(pk='569228a9b37b3301e0706b51'))
        self.assertEqual(item.wholesale_price, 0)  # wholesale_price remains unchanged
        self.assertIsNone(item.max_price)  # max_price is None
        self.assertEqual(item.retail_price, 600)  # retail_price cannot be bigger than max_price
        self.assertEqual(item.description, 'Some description')

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103',
                       IS_RETAILER=True, IS_PROVIDER=False)
    def test_submit_item_with_existing_item(self):
        """
        submit_item view updates item information if it previously exists.
        Only retail_price can be set if user is a Retailer
        """
        copy_service_and_config_to_default_db()
        call_command('loaddata', 'wn_members.yaml', database=UMBRELLA)
        call_command('loaddata', 'wn_setup_data.yaml')
        call_command('loaddata', 'wn_operators_configs.yaml')
        call_command('loaddata', 'items.yaml')
        self.client.login(username='member3', password='admin')
        item = Item.objects.get(pk='55d1fa8feb60008099bd4152')
        item.provider = get_service_instance()  # Make provider of this item the current retailer
        item.save()
        p_dict = item.__dict__
        p_dict['category'] = '569228a9b37b3301e0706b51'
        p_dict['name'] = 'Black Chocolate'
        p_dict['brand'] = 'Mambo'
        p_dict['summary'] = 'Some summary'
        p_dict['description'] = 'Some description'
        p_dict['retail_price'] = 500
        response = self.client.post(reverse('items:change_item', args=('55d1fa8feb60008099bd4152', )), p_dict)
        item = Item.objects.get(pk='55d1fa8feb60008099bd4152')
        self.assertEqual(item.name, 'Black Chocolate')
        self.assertEqual(item.slug, 'black-chocolate')  # Slug must be correctly set
        self.assertEqual(item.category, ItemCategory.objects.get(pk='569228a9b37b3301e0706b51'))
        self.assertEqual(item.retail_price, 500)
        self.assertEqual(item.summary, 'Some summary')
        self.assertEqual(item.description, 'Some description')

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b102',
                       IS_PROVIDER=True)
    def test_submit_item_with_existing_item_being_retailed(self):
        """
        submit_item view redirects to the add_view page without actually updating item information
        if a provider attemps to update information of a item being retailed.
        """
        call_command('loaddata', 'wn_members.yaml', database=UMBRELLA)
        copy_service_and_config_to_default_db()
        service = Service.objects.using(UMBRELLA).get(pk='56eb6d04b37b3379b531b102')
        add_database_to_settings(service.database)
        call_command('loaddata', 'items.yaml')
        self.client.login(username='member2', password='admin')
        item = Item.objects.get(pk='55d1fa8feb60008099bd4152')
        item.is_retailed = True
        item.save()
        p_dict = item.__dict__
        p_dict['category'] = p_dict['category_id']
        p_dict['retail_price'] = 500
        response = self.client.post(reverse('items:change_item', args=('55d1fa8feb60008099bd4152', )), p_dict)
        self.assertIsNotNone(response.context['error'])
        item = Item.objects.get(pk='55d1fa8feb60008099bd4152')
        self.assertEqual(item.retail_price, 450)

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_submit_item_with_new_service(self):
        """
        submit_item view can only update retail_price of services
        """
        copy_service_and_config_to_default_db()
        call_command('loaddata', 'wn_members.yaml', database=UMBRELLA)
        call_command('loaddata', 'items.yaml')
        self.client.login(username='member3', password='admin')
        response = self.client.post(reverse('items:change_item'),
                                   {'item_type': 'service',
                                    'name': 'Auto Insurance', 'brand': '',
                                    'category': '569228a9b37b3301e0706b54',
                                    'duration': '91',
                                    'duration_text': '3 mois',
                                    'wholesale_price': '0',
                                    'retail_price': '6000',
                                    'summary': 'Some summary',
                                    'description': 'Some description'})
        service = RecurringPaymentService.objects.get(slug='auto-insurance')  # Slug must be correctly set
        self.assertEqual(service.name, 'Auto Insurance')
        self.assertEqual(service.category, ItemCategory.objects.get(pk='569228a9b37b3301e0706b54'))
        self.assertEqual(service.wholesale_price, 0)  # wholesale_price remains unchanged
        self.assertIsNone(service.max_price)  # max_price is None
        self.assertEqual(service.retail_price, 6000)  # retail_price cannot be bigger than max_price
        self.assertEqual(service.summary, 'Some summary')
        self.assertEqual(service.description, 'Some description')

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_submit_item_with_existing_service(self):
        """
        submit_item view update information of a previously existing RecurringPaymentService
        """
        copy_service_and_config_to_default_db()
        call_command('loaddata', 'wn_members.yaml', database=UMBRELLA)
        call_command('loaddata', 'items.yaml')
        self.client.login(username='member3', password='admin')
        service = RecurringPaymentService.objects.get(pk='55d1fa8feb60008099bd4154')
        service.provider = get_service_instance()  # Make provider of this service the current retailer
        service.save()
        response = self.client.post(reverse('items:change_item'),
                                   {'item_id': '55d1fa8feb60008099bd4154',
                                    'category': '569228a9b37b3301e0706b54',
                                    'name': 'Loss insurance',
                                    'item_type': 'service',
                                    'duration': service.duration,
                                    'duration_text': service.duration_text,
                                    'retail_price': '6000',
                                    'summary': 'Some summary',
                                    'description': 'Some description'})
        service = RecurringPaymentService.objects.get(pk='55d1fa8feb60008099bd4154')
        self.assertEqual(service.name, 'Loss insurance')
        self.assertEqual(service.slug, 'loss-insurance')  # Slug must be correctly set
        self.assertEqual(service.category, ItemCategory.objects.get(pk='569228a9b37b3301e0706b54'))
        self.assertEqual(service.retail_price, 6000)  # retail_price cannot be bigger than max_price
        self.assertEqual(service.summary, 'Some summary')
        self.assertEqual(service.description, 'Some description')

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b102',
                       IS_PROVIDER=True)
    def test_delete_item_with_item_being_in_a_smart_category(self):
        """
        Deleting a item decrements the items_count
        of Category or SmartCategory it belongs to 
        """
        call_command('loaddata', 'wn_members.yaml', database=UMBRELLA)
        call_command('loaddata', 'wn_setup_data.yaml')
        call_command('loaddata', 'wn_operators_configs.yaml')
        call_command('loaddata', 'categories.yaml')
        call_command('loaddata', 'items.yaml')
        call_command('loaddata', 'smart_objects.yaml')
        obj = SmartCategory.objects.get(pk='56a9b37b3301e0706b549224')
        obj.items_count = 1
        obj.items_fk_list.append('55d1fa8feb60008099bd4152')
        obj.save()
        self.client.login(username='member2', password='admin')
        self.client.get(reverse('items:put_item_in_trash'), {'selection': '55d1fa8feb60008099bd4152'})
        category = ItemCategory.objects.get(pk='569228a9b37b3301e0706b52')
        smart_category = SmartCategory.objects.get(pk='56a9b37b3301e0706b549224')
        self.assertEqual(category.items_count, 1)
        self.assertEqual(smart_category.items_count, 0)
        self.assertListEqual(smart_category.items_fk_list, [])

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b102')
    def test_delete_category_with_category_being_in_a_smart_category(self):
        """
        Deleting a item decrements the items_count
        of Category or SmartCategory it belongs to 
        """
        call_command('loaddata', 'wn_members.yaml', database=UMBRELLA)
        call_command('loaddata', 'wn_setup_data.yaml')
        call_command('loaddata', 'wn_operators_configs.yaml')
        call_command('loaddata', 'categories.yaml')
        call_command('loaddata', 'smart_objects.yaml')
        obj = SmartCategory.objects.get(pk='56a9b37b3301e0706b549223')
        obj.items_count = 1
        obj.items_fk_list.append('569228a9b37b3301e0706b52')
        obj.save()
        self.client.login(username='member2', password='admin')
        response = self.client.get(reverse('items:delete_category'),
                                   {'selection': '569228a9b37b3301e0706b52'})
        smart_category = SmartCategory.objects.get(pk='56a9b37b3301e0706b549223')
        self.assertEqual(smart_category.items_count, 0)
        self.assertListEqual(smart_category.items_fk_list, [])

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_do_import_items_from_spreadsheet_with_unauthorized_member(self):
        """
        Unauthorized member cannot import item
        """
        copy_service_and_config_to_default_db()
        response = self.client.get(reverse('items:do_import_items_from_spreadsheet'))
        self.assertEqual(response.status_code, 302)

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103',
                       MEDIA_ROOT='')
    def test_do_import_items_from_spreadsheet(self):
        """
        Importing items merely pulls a list of items from an Excel file into the database
        """
        media_root = getattr(settings, 'BASE_DIR') + '/'
        setattr(settings, 'MEDIA_ROOT', media_root)
        call_command('loaddata', 'wn_members.yaml', database=UMBRELLA)
        call_command('loaddata', 'items.yaml')
        copy_service_and_config_to_default_db()
        Item.objects.all().delete()
        self.client.login(username='member3', password='admin')
        response = self.client.get(reverse('items:do_import_items_from_spreadsheet'), {'upload_id': '56eb6d779b33b531e09104b1'})
        response = json.loads(response.content)
        self.assertTrue(response['success'])
        self.assertEqual(Item.objects.all().count(), 2)


    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b102',
                       IS_PROVIDER=True, IS_RETAILER=False,
                       EMAIL_BACKEND='django.core.mail.backends.filebased.EmailBackend',
                       EMAIL_FILE_PATH='test_emails/items/')
    def test_put_item_in_trash(self):
        """
        set_stock causes the stock to lower or raise by the number of units, all passed as GET parameters
        """
        call_command('loaddata', 'wn_members.yaml', database=UMBRELLA)
        copy_service_and_config_to_default_db()
        service = Service.objects.using(UMBRELLA).get(pk='56eb6d04b37b3379b531b103')
        add_database_to_settings(service.database)
        call_command('loaddata', 'wn_setup_data.yaml', database='default')
        call_command('loaddata', 'items.yaml', database='default')
        call_command('loaddata', 'wn_operators_configs.yaml', database='default')
        call_command('loaddata', 'categories.yaml', database=service.database)
        call_command('loaddata', 'items.yaml', database=service.database)
        Item.objects.using('default').all().update(is_retailed=True)
        self.client.login(username='member2', password='admin')
        response = self.client.get(reverse('items:put_item_in_trash') + '?selection=55d1fa8feb60008099bd4152')
        response = json.loads(response.content)
        self.assertIsNotNone(response['message'])
        item = Item.objects.using(service.database).filter(pk='55d1fa8feb60008099bd4152')
        self.assertEqual(item.count(), 0)
        member3 = Member.objects.using(UMBRELLA).get(username='member3')
        self.assertEqual(member3.personal_notices, 1)
        self.assertEqual(ConsoleEvent.objects.using(UMBRELLA).filter(member=member3).count(), 1)

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b107', IS_BANK=True, LOCAL_DEV=False,
                       EMAIL_BACKEND='django.core.mail.backends.filebased.EmailBackend',
                       EMAIL_FILE_PATH='test_emails/items/')
    def test_load_item_from_url_with_unregistered_partner(self):
        """
        Items from unregistered partner cannot be loaded.
        """
        for alias in ('default', 'test_kc_tecnomobile'):
            call_command('loaddata', 'wn_setup_data.yaml', database=alias)
            call_command('loaddata', 'wn_operators_configs.yaml', database=alias)
        call_command('loaddata', 'categories.yaml', database='test_kc_tecnomobile')
        call_command('loaddata', 'items.yaml', database='test_kc_tecnomobile')
        Service.objects.filter(project_name='tecnomobile').delete()
        OperatorProfile.objects.filter(company_name='Tecno Mobile Telecom').delete()

        url = 'http://tecnomobile.ikwen.com/phones-and-tablets/samsung-galaxy-s7'
        self.client.login(username='member7', password='admin')
        response = self.client.get(reverse('items:load_item_from_url'), {'url': url})
        response = json.loads(response.content)
        self.assertEqual(response['error'], 'You must add Tecno Mobile Telecom as a Partner Merchant to import his items.')

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b107', IS_BANK=True, LOCAL_DEV=False,
                       EMAIL_BACKEND='django.core.mail.backends.filebased.EmailBackend',
                       EMAIL_FILE_PATH='test_emails/items/')
    def test_load_item_from_url_with_registered_partner(self):
        """
        Retrieves item an merchant based on URL of item
        """
        for alias in ('default', 'test_kc_tecnomobile'):
            call_command('loaddata', 'wn_setup_data.yaml', database=alias)
            call_command('loaddata', 'wn_operators_configs.yaml', database=alias)
        call_command('loaddata', 'categories.yaml', database='test_kc_tecnomobile')
        call_command('loaddata', 'items.yaml', database='test_kc_tecnomobile')
        url = 'http://tecnomobile.ikwen.com/phones-and-tablets/samsung-galaxy-s7'
        self.client.login(username='member7', password='admin')
        response = self.client.get(reverse('items:load_item_from_url'), {'url': url})
        response = json.loads(response.content)
        self.assertEqual(response['item']['slug'], 'samsung-galaxy-s7')  # Item has been correctly retrieved

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b107', IS_BANK=True, LOCAL_DEV=False,
                       EMAIL_BACKEND='django.core.mail.backends.filebased.EmailBackend',
                       EMAIL_FILE_PATH='test_emails/items/')
    def test_save_item_from_url_with_registered_partner(self):
        """
        Retrieves item an merchant based on URL of item
        """
        for alias in ('umbrella', 'test_kc_tecnomobile'):
            call_command('loaddata', 'wn_members.yaml', database=alias)
        for alias in ('default', 'test_kc_tecnomobile'):
            call_command('loaddata', 'wn_setup_data.yaml', database=alias)
            call_command('loaddata', 'wn_operators_configs.yaml', database=alias)
        call_command('loaddata', 'categories.yaml', database='test_kc_tecnomobile')
        call_command('loaddata', 'items.yaml', database='test_kc_tecnomobile')
        Item.objects.all().delete()

        url = 'http://tecnomobile.ikwen.com/phones-and-tablets/samsung-galaxy-s7'
        self.client.login(username='member7', password='admin')
        response = self.client.get(reverse('items:save_item_from_url'), {'url': url})
        self.assertEqual(response.status_code, 302)
        Item.objects.get(slug='samsung-galaxy-s7')  # Item has been correctly saved locally
