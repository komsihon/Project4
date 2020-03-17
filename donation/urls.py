from django.conf.urls import patterns, include, url

from django.contrib import admin
from django.contrib.auth.decorators import permission_required
from ikwen_webnode.donation.views import DonationView, ListDonation, ChangeDonation
from ikwen_webnode.donation.paypal.views import SetExpressCheckout, GetExpressCheckoutDetails, DoExpressCheckout, PayPalCancel

admin.autodiscover()

urlpatterns = patterns('',
        url(r'^$', DonationView.as_view(), name='home'),

        url(r'^paypal/setCheckout/$', SetExpressCheckout.as_view(), name='paypal_set_checkout'),
        url(r'^paypal/setCheckout/', SetExpressCheckout.as_view(), name='paypal_set_checkout'),
        url(r'^paypal/getDetails/$', GetExpressCheckoutDetails.as_view(), name='paypal_get_details'),
        url(r'^paypal/doCheckout/$', DoExpressCheckout.as_view(), name='paypal_do_checkout'),
        url(r'^paypal/cancel/$', PayPalCancel.as_view(), name='paypal_cancel'),

        url(r'^list/$', permission_required('items.ik_manage_item')(ListDonation.as_view()), name='donation_list'),
        url(r'^bounty/$', permission_required('items.ik_manage_item')(ChangeDonation.as_view()),
            name='change_donation'),
        url(r'^bounty/(?P<cbounty_id>[-\w]+)/$', permission_required('items.ik_manage_item')(ChangeDonation.as_view()),
            name='change_donation'),
        # url(r'^delete_donation$', delete_donation, name='delete_donation'),
    )
