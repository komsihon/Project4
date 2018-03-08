from django.core.management import call_command
from django.test.client import Client
from django.test.utils import override_settings
from django.utils import unittest
from ikwen.core.models import Service

from ikwen.accesscontrol.models import Member

from ikwen_webnode.web.models import Banner, SLIDE
from ikwen.accesscontrol.backends import UMBRELLA
from ikwen_webnode.items.models import Item, ItemCategory
from ikwen_webnode.items.tests_views import wipe_test_data
from ikwen_webnode.items.utils import create_category, mark_duplicates, get_item_from_url
from ikwen_kakocase.kakocase.models import OperatorProfile


class KakoUtilsTestCase(unittest.TestCase):
    """
    This test derives django.utils.unittest.TestCate rather than the default django.test.TestCase.
    Thus, self.client is not automatically created and fixtures not automatically loaded. This
    will be achieved manually by a custom implementation of setUp()
    """
    fixtures = ['wn_members.yaml', 'wn_profiles.yaml', 'wn_setup_data.yaml', 'wn_operators_configs.yaml',
                'categories.yaml', 'items.yaml']

    def setUp(self):
        self.client = Client()
        for fixture in self.fixtures:
            call_command('loaddata', fixture)

    def tearDown(self):
        wipe_test_data()
        wipe_test_data('test_kc_tecnomobile')


    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_create_category(self):
        """
        Creating a category creates it in local database.
        """
        create_category(name='New category')
        category = ItemCategory.objects.get(slug='new-category')
        self.assertEqual(category.name, 'New category')  # Upon creation, name is capitalized


    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_Item_delete(self):
        """
        Product.get_size_list returns a list of all sizes of Products with same slug, category and brand.
        """
        Banner.objects.create(title='Banner',  display=SLIDE,
                              items_fk_list=['55d1fa8feb60008099bd4151', '55d1fa8feb60008099bd4152'])
        p1 = Item.objects.get(pk='55d1fa8feb60008099bd4151')
        p1.delete()
        banner = Banner.objects.get(title='Banner')
        self.assertListEqual(banner.items_fk_list, ['55d1fa8feb60008099bd4152'])

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b107', LOCAL_DEV=False)
    def test_get_item_from_url(self):
        """
        Retrieves product an merchant based on URL of product
        """
        call_command('loaddata', 'wn_setup_data.yaml', database='umbrella')
        call_command('loaddata', 'categories.yaml', database='test_kc_tecnomobile')
        call_command('loaddata', 'items.yaml', database='test_kc_tecnomobile')
        url = 'http://tecnomobile.ikwen.com/phones-and-tablets/samsung-galaxy-s7'
        item, merchant = get_item_from_url(url)
        self.assertEqual(item.slug, 'samsung-galaxy-s7')
        self.assertEqual(merchant.id, '56eb6d04b37b3379b531b101')
