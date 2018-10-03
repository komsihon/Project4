# -*- coding: utf-8 -*-
import random
import string
import requests
import json

from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.utils.http import urlunquote
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import TemplateView

from ikwen.billing.models import PaymentMean
from ikwen_webnode.donation.views import donation_do_checkout

from ikwen.core.utils import get_service_instance, parse_paypal_response, EC_ENDPOINT
from ikwen_webnode.donation.views import confirm_checkout, TemplateSelector


class SetExpressCheckout(TemplateView):
    template_name = 'donation/institution/home.html'

    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def post(self, request, *args, **kwargs):
        service = get_service_instance()
        config = service.config
        payment_mean = PaymentMean.objects.get(slug='paypal')
        if getattr(settings, 'DEBUG', False):
            paypal = json.loads(payment_mean.credentials)
        else:
            try:
                paypal = json.loads(payment_mean.credentials)
            except:
                return HttpResponse("Error, Could not parse PayPal parameters.")

        amount = request.POST["amount"]

        if getattr(settings, 'UNIT_TESTING', False):
            signature = 'dumb_signature'
        else:
            signature = ''.join([random.SystemRandom().choice(string.ascii_letters + string.digits) for n in range(16)])
        request.session['amount'] = amount
        request.session['signature'] = signature
        request.session['return_url'] = service.url + reverse('donation:home')

        if getattr(settings, 'UNIT_TESTING', False):
            return HttpResponse(json.dumps({"amount": amount}))

        line_items = {
            "L_PAYMENTREQUEST_0_NAME0": 'Donation',
            "L_PAYMENTREQUEST_0_DESC0": '<' + _("No description") + '>',
            "L_PAYMENTREQUEST_0_AMT0": amount,
            "L_PAYMENTREQUEST_0_QTY0": 1,
            "L_PAYMENTREQUEST_0_TAXAMT0": 0,
            "L_PAYMENTREQUEST_0_NUMBER0": 1,
            "L_PAYMENTREQUEST_0_ITEMURL0": service.url + reverse('donation:home'),
            "L_PAYMENTREQUEST_0_ITEMCATEGORY0": 'Physical'
        }

        ec_data = {
            "USER": paypal['username'],
            "PWD": paypal['password'],
            "SIGNATURE": paypal['signature'],
            "METHOD": "SetExpressCheckout",
            "VERSION": 124.0,
            "RETURNURL": service.url + reverse('donation:paypal_get_details') + '?amount=' + amount,
            "CANCELURL": service.url + reverse('donation:paypal_cancel'),
            "PAYMENTREQUEST_0_PAYMENTACTION": "Sale",
            "PAYMENTREQUEST_0_AMT": amount,
            "PAYMENTREQUEST_0_ITEMAMT": amount,
            "PAYMENTREQUEST_0_SHIPPINGAMT": 0,
            "PAYMENTREQUEST_0_TAXAMT": 0,
            "PAYMENTREQUEST_0_CURRENCYCODE": "EUR",
            "PAYMENTREQUEST_0_DESC": "Donation on " + service.project_name
        }
        ec_data.update(line_items)
        try:
            response = requests.post(EC_ENDPOINT, data=ec_data)
            result = parse_paypal_response(response.content.decode('utf-8'))
            ACK = result['ACK']
            if ACK == 'Success' or ACK == 'SuccessWithWarning':
                if getattr(settings, 'DEBUG', False):
                    redirect_url = 'https://www.sandbox.paypal.com/checkoutnow?token=' + result['TOKEN']
                else:
                    redirect_url = 'https://www.paypal.com/checkoutnow?token=' + result['TOKEN']
                return HttpResponseRedirect(redirect_url)
            else:
                context = self.get_context_data(**kwargs)
                if getattr(settings, 'DEBUG', False):
                    context['paypal_error'] = urlunquote(response.content.decode('utf-8'))
                else:
                    context['paypal_error'] = urlunquote(result['L_LONGMESSAGE0'])
                return render(request, 'donation/institution/home.html', context)
        except Exception as e:
            if getattr(settings, 'DEBUG', False):
                raise e
            context = self.get_context_data(**kwargs)
            context['server_error'] = 'Could not initiate transaction due to server error. Contact administrator.'
            return render(request, 'donation/institution/home.html', context)


class GetExpressCheckoutDetails(TemplateView):
    template_name = 'donation/paypal/confirmation.html'

    def get(self, request, *args, **kwargs):
        paypal = json.loads(PaymentMean.objects.get(slug='paypal').credentials)
        paypal_token = request.GET['token']
        ec_data = {
            "USER": paypal['username'],
            "PWD": paypal['password'],
            "SIGNATURE": paypal['signature'],
            "METHOD": "GetExpressCheckoutDetails",
            "VERSION": 124.0,
            "TOKEN": paypal_token
        }
        try:
            response = requests.post(EC_ENDPOINT, data=ec_data)
            result = parse_paypal_response(response.content.decode('utf-8'))
            ACK = result['ACK']
            if ACK == 'Success' or ACK == 'SuccessWithWarning':
                request.session['token'] = paypal_token
                request.session['payer_id'] = request.GET['PayerID']
                context = self.get_context_data(**kwargs)
                context['amount'] = urlunquote(result['PAYMENTREQUEST_0_AMT'])
                return render(request, self.template_name, context)
            else:
                context = self.get_context_data(**kwargs)
                if getattr(settings, 'DEBUG', False):
                    context['paypal_error'] = urlunquote(response.content.decode('utf-8'))
                else:
                    context['paypal_error'] = urlunquote(result['L_LONGMESSAGE0'])
                return render(request, 'donation/paypal/cancel.html', context)
        except Exception as e:
            if getattr(settings, 'DEBUG', False):
                raise e
            context = self.get_context_data(**kwargs)
            context['server_error'] = 'Could not proceed transaction due to server error. Contact administrator.'
            return render(request, 'donation/paypal/cancel.html', context)


class DoExpressCheckout(TemplateSelector, TemplateView):
    template_name = 'donation/institution/home.html'

    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def post(self, request, *args, **kwargs):
        if getattr(settings, 'UNIT_TESTING', False):
            return confirm_checkout(request, signature=request.session['signature'], *args, **kwargs)

        service = get_service_instance()
        paypal = json.loads(PaymentMean.objects.get(slug='paypal').credentials)
        amount = request.POST['amount']
        line_items = {
            "L_PAYMENTREQUEST_0_NAME0": "Donation",
            "L_PAYMENTREQUEST_0_DESC0": '<' + _("No description") + '>',
            "L_PAYMENTREQUEST_0_AMT0": amount,
            "L_PAYMENTREQUEST_0_QTY0": 1,
            "L_PAYMENTREQUEST_0_TAXAMT0": 0,
            "L_PAYMENTREQUEST_0_NUMBER0": 1,
            "L_PAYMENTREQUEST_0_ITEMURL0":  service.url + reverse('donation:home'),
            "L_PAYMENTREQUEST_0_ITEMCATEGORY0": 'Physical'
        }
        ec_data = {
            "USER": paypal['username'],
            "PWD": paypal['password'],
            "SIGNATURE": paypal['signature'],
            "METHOD": "DoExpressCheckoutPayment",
            "VERSION": 124.0,
            "TOKEN": request.session['token'],
            "PAYERID": request.session['payer_id'],
            "PAYMENTREQUEST_0_PAYMENTACTION": "Sale",
            "PAYMENTREQUEST_0_AMT": amount,
            "PAYMENTREQUEST_0_ITEMAMT": amount,
            "PAYMENTREQUEST_0_SHIPPINGAMT": 0,
            "PAYMENTREQUEST_0_TAXAMT": 0,
            "PAYMENTREQUEST_0_CURRENCYCODE": "EUR",
            "PAYMENTREQUEST_0_DESC": "Donation on " + service.project_name
        }
        ec_data.update(line_items)
        if getattr(settings, 'DEBUG', False):
            response = requests.post(EC_ENDPOINT, data=ec_data)
            result = parse_paypal_response(response.content.decode('utf-8'))
            ACK = result['ACK']
            if ACK == 'Success' or ACK == 'SuccessWithWarning':
                request.session['mean'] = 'paypal'
                return donation_do_checkout(request, signature=request.session['signature'], *args, **kwargs)
            else:
                context = self.get_context_data(**kwargs)
                if getattr(settings, 'DEBUG', False):
                    context['paypal_error'] = urlunquote(response.content.decode('utf-8'))
                else:
                    context['paypal_error'] = urlunquote(result['L_LONGMESSAGE0'])
                return render(request, 'donation/institution/home.html', context)
        else:
            try:
                response = requests.post(EC_ENDPOINT, data=ec_data)
                result = parse_paypal_response(response.content.decode('utf-8'))
                ACK = result['ACK']
                if ACK == 'Success' or ACK == 'SuccessWithWarning':
                    return confirm_checkout(request, signature=request.session['signature'], *args, **kwargs)
                else:
                    context = self.get_context_data(**kwargs)
                    if getattr(settings, 'DEBUG', False):
                        context['paypal_error'] = urlunquote(response.content.decode('utf-8'))
                    else:
                        context['paypal_error'] = urlunquote(result['L_LONGMESSAGE0'])
                    return render(request,'donation/paypal/cancel.html', context)
            except Exception as e:
                context = self.get_context_data(**kwargs)
                context['server_error'] = 'Could not proceed transaction due to server error. Contact administrator.'
                return render(request, 'donation/paypal/cancel.html', context)


class PayPalCancel(TemplateView):
    template_name = 'donation/paypal/cancel.html'
