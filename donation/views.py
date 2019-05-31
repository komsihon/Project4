import os, json, random
from threading import Thread
from django.core.mail.message import EmailMessage

from ajaxuploader.views import AjaxFileUploader
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views.generic import TemplateView
from django.core.urlresolvers import reverse
from django.forms.models import modelform_factory
from django.http.response import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.contrib.admin import helpers
from django.contrib import messages
from django.utils.translation import gettext as _

from ikwen.billing.utils import share_payment_and_set_stats
from ikwen.core.constants import CONFIRMED
from ikwen.billing.models import Donation

from ikwen.billing.models import Donation
from ikwen.core.utils import get_service_instance, logger, as_matrix, get_mail_content
from ikwen_webnode.donation.admin import DonationAdmin
from django.http import HttpResponse
from ikwen.core.views import HybridListView, ChangeObjectBase
from ikwen_webnode.webnode.views import TemplateSelector
from ikwen_webnode.donation.models import Bounty
from ikwen.billing.mtnmomo.views import MTN_MOMO
from ikwen.billing.orangemoney.views import ORANGE_MONEY

EURO_RATE = 655


class DonationView(TemplateSelector, TemplateView):
    template_name = 'donation/home.html'


class DonationList(TemplateSelector, TemplateView):
    template_name = 'donation/home.html'

    def get_context_data(self, **kwargs):
        context = super(DonationList, self).get_context_data(**kwargs)
        donations = Donation.objects.filter(is_active=True)
        context['donations'] = donations
        return context


class ListDonation(HybridListView):
    template_name = 'donation/admin/donation_list.html'
    model = Donation
    ordering = ('-id',)
    search_field = 'name'
    context_object_name = 'donation_list'

    def get_context_data(self, **kwargs):
        context = super(ListDonation, self).get_context_data(**kwargs)
        donations = Donation.objects.all()
        context['donations'] = donations
        return context


class ChangeDonation(ChangeObjectBase):
    model = Donation
    model_admin = DonationAdmin
    context_object_name = 'donation'
    template_name = 'donation/admin/change_donation.html'


def toggle_object_attribute(request, *args, **kwargs):
    object_id = request.GET['object_id']
    attr = request.GET['attr']
    val = request.GET['val']
    try:
        obj = Donation.objects.get(pk=object_id)
    except Donation.DoesNotExist:
        obj = Donation.objects.get(pk=object_id)
    if val.lower() == 'true':
        obj.__dict__[attr] = True
    else:
        obj.__dict__[attr] = False
    obj.save()
    response = {'success': True}
    return HttpResponse(json.dumps(response), 'content-type: text/json')


def donation_set_checkout(request, *args, **kwargs):
    service = get_service_instance()
    member = request.user
    euro_amount = float(request.POST['amount'])
    raw_amount = euro_amount * EURO_RATE
    amount = raw_amount - (raw_amount % 50)
    message = request.POST.get('message')
    if member.is_authenticated() and not request.POST.get('anonymous_donation'):
        donation = Donation.objects.create(member=member, amount=amount, message=message)
    else:
        donation = Donation.objects.create(amount=amount, message=message)
    request.session['amount'] = donation.amount
    request.session['model_name'] = 'billing.Donation'
    request.session['object_id'] = donation.id

    mean = request.GET.get('mean', MTN_MOMO)
    request.session['mean'] = mean
    request.session['notif_url'] = service.url # Orange Money only
    request.session['cancel_url'] = service.url + reverse('donation:home') # Orange Money only
    request.session['return_url'] = service.url + reverse('donation:home')


def confirm_checkout(request, *args, **kwargs):
    bounty_amount = request.session['amount']

    if request.user.is_authenticated():
        user_name = request.user.full_name
        user_email = request.user.email

        subject = _("Thank you for your donation")
        msg = ("Your donation of %s euros was successfully procceded. Thank for your trust" % (bounty_amount))
        send_confirmation_email(subject, user_name, user_email, bounty_amount, msg)
    logger.info("Donation of %s Euros successfully proceeded" % (bounty_amount))

    next_url = reverse('donation:home', args=('success',))
    request.session.modified = True

    if request.session.get('is_momo_payment'):
        return {'success': True, 'next_url': next_url}
    else:
        return HttpResponseRedirect(next_url)


def donation_do_checkout(request, *args, **kwargs):
    donation_id = request.session['object_id']
    mean = request.session['mean']
    donation = Donation.objects.get(pk=donation_id)
    donation.status = CONFIRMED
    donation.save()
    share_payment_and_set_stats(donation, payment_mean_slug=mean)

    service = get_service_instance()
    # config = service.config
    # if member.email:
    #     subject, message, sms_text = get_payment_confirmation_message(payment, member)
    #     html_content = get_mail_content(subject, message, template_name='billing/mails/notice.html')
    #     sender = '%s <no-reply@%s>' % (config.company_name, service.domain)
    #     msg = EmailMessage(subject, html_content, sender, [member.email])
    #     msg.content_subtype = "html"
    #     Thread(target=lambda m: m.send(), args=(msg,)).start()
    messages.success(request, _("Successful payment. Thank you soooo much for your donation."))
    return HttpResponseRedirect(request.session['return_url'])


def send_confirmation_email(subject, buyer_name, buyer_email, order, message=None):
    service = get_service_instance()
    html_content = get_mail_content(subject, '', template_name='tsunami/mails/order_notice.html',
                                    extra_context={'buyer_name': buyer_name, 'order': order, 'message': message})
    sender = '%s <no-reply@%s>' % (service.project_name, service.domain)
    msg = EmailMessage(subject, html_content, sender, [buyer_email])
    bcc = [service.member.email, service.config.contact_email]
    msg.bcc = list(set(bcc))
    msg.content_subtype = "html"
    Thread(target=lambda m: m.send(), args=(msg,)).start()

