import json

from django.core.management import call_command
from django.core.urlresolvers import reverse
from django.test.client import Client
from django.test.utils import override_settings
from django.utils import unittest
from ikwen_webnode.items.models import ItemCategory
from ikwen_webnode.web.models import FLAT_PAGE

from commarketing.models import Banner, CATEGORIES, SmartCategory, SLIDE
from ikwen_kakocase.kako.tests_views import wipe_test_data


class WebNodeTestCase(unittest.TestCase):
    """
    This test derives django.utils.unittest.TestCate rather than the default django.test.TestCase.
    Thus, self.client is not automatically created and fixtures not automatically loaded. This
    will be achieved manually by a custom implementation of setUp()
    """
    fixtures = ['wn_members.yaml', 'wn_setup_data.yaml', 'wn_operators_configs.yaml', 'items.yaml', 'wn_smart_objects.yaml']

    def setUp(self):
        self.client = Client()
        call_command('loaddata', 'wn_setup_data.yaml', database='umbrella')
        call_command('loaddata', 'wn_operators_configs.yaml', database='umbrella')
        for fixture in self.fixtures:
            call_command('loaddata', fixture)

    def tearDown(self):
        wipe_test_data()
        # wipe_test_data(UMBRELLA)

# Slug must be correctly set

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_Webnode_pages(self):
        """
        Must create a new SmartCategory in the database. SmartObjectList must return HTTP 200 after the operation
        """
        response = self.client.get(reverse('webnode:home'))
        self.assertEqual(response.status_code, 200)
        slideshow = response.context['slideshow']
        homepage_section_list = response.context['homepage_section_list']
        flat_pages = response.context['flat_pages']
        self.assertEqual(slideshow.count(), 3)
        self.assertEqual(homepage_section_list.count(), 1)
        self.assertEqual(flat_pages.count(), 0)

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_ItemList_page(self):
        """
        Must create a new SmartCategory in the database. SmartObjectList must return HTTP 200 after the operation
        """
        response = self.client.get(reverse('webnode:item_list', kwargs={'slug': 'services'}))
        self.assertEqual(response.status_code, 200)
        item_list = response.context['item_list']
        self.assertEqual(len(item_list), 0)

    @override_settings(IKWEN_SERVICE_ID='56eb6d04b37b3379b531b103')
    def test_ItemDetails_page(self):
        """
        Must create a new SmartCategory in the database. SmartObjectList must return HTTP 200 after the operation
        """
        response = self.client.get(reverse('webnode:product_details', kwargs={"category_slug": 'drinks', 'slug': 'coca-cola'}))
        self.assertEqual(response.status_code, 200)
        item = response.context['item']
        self.assertEqual(item.id, '55d1fa8feb60008099bd4152')
