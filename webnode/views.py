import json
import datetime
from django.http import HttpResponse
from django.views.generic import TemplateView
from ikwen.accesscontrol.models import Member
from ikwen.billing.models import CloudBillingPlan, IkwenInvoiceItem, InvoiceEntry
from ikwen.core.utils import get_service_instance
from ikwen.flatpages.models import FlatPage
from ikwen.partnership.models import ApplicationRetailConfig
from ikwen.theming.models import Theme, Template
from django.conf import settings
from ikwen.accesscontrol.backends import UMBRELLA
from ikwen.core.models import Service, Application

from django.core.urlresolvers import reverse
from django.http.response import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django.utils.http import urlquote
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from ikwen_webnode.web.models import Banner, SmartCategory, SLIDE, HomepageSection
from ikwen_webnode.items.models import ItemCategory, Item
from ikwen.core.utils import as_matrix
import random


from ikwen_webnode.blog.models import Post

# from ikwen_webnode.conf import settings
from ikwen_webnode.webnode.cloud_setup import deploy, DeploymentForm

COZY = "Cozy"
COMPACT = "Compact"
COMFORTABLE = "Comfortable"
HOME = 'home'
POST_PER_PAGE = 5


class TemplateSelector(object):
    def get_template_names(self):
        config = get_service_instance().config
        if config.theme and config.theme.template.slug != "":
            if config.theme.template.slug == 'optimum':
                config.theme.template.slug = "improve"
            tokens = self.template_name.split('/')
            tokens.insert(1, config.theme.template.slug)
            return ['/'.join(tokens)]
        return [self.template_name]


class Home(TemplateSelector, TemplateView):
    template_name = 'webnode/home.html'

    def get_context_data(self, **kwargs):
        context = super(Home, self).get_context_data(**kwargs)
        context['slideshow'] = Banner.objects.filter(display=SLIDE, is_active=True).order_by('order_of_appearance')
        context['homepage_section_list'] = HomepageSection.objects.filter(is_active=True).order_by('order_of_appearance')
        return context


class AdminHome(TemplateSelector, TemplateView):
    template_name = 'admin_home.html'


class ItemDetails(TemplateSelector, TemplateView):
    template_name = 'webnode/detail.html'

    def get_context_data(self, **kwargs):
        context = super(ItemDetails, self).get_context_data(**kwargs)
        slug = kwargs['slug']
        category_slug = kwargs['category_slug']
        category = ItemCategory.objects.get(slug=category_slug)
        page_item = Item.objects.get(slug=slug, category=category, in_trash=False, visible=True)
        tags = page_item.tags
        tag_list = tags.split(' ')
        blog_suggestions = []
        for tag in tag_list:
            posts = Post.objects.filter(title__icontains=tag, is_active=True)
            for post in posts:
                blog_suggestions.append(post)
        items_qs = Item.objects.filter(category=category, visible=True)
        suggestions =[]
        for item in items_qs:
            if item != page_item:
                suggestions.append(item)

        random.shuffle(suggestions)
        context['item'] = page_item
        context['page_suggestions'] = suggestions[:4]
        context['blog_suggestions'] = blog_suggestions[:3]
        return context


class ItemList(TemplateSelector, TemplateView):
    template_name = 'webnode/item_list.html'

    def _get_row_len(self):
        config = get_service_instance().config
        if config.theme and config.theme.display == COMFORTABLE:
            return 2
        elif config.theme and config.theme.display == COZY:
            return 3
        else:
            return getattr(settings, 'PRODUCTS_PREVIEWS_PER_ROW', 4)

    def get_context_data(self, **kwargs):
        context = super(ItemList, self).get_context_data(**kwargs)
        slug = kwargs['slug']
        try:
            smart_category = SmartCategory.objects.get(slug=slug)
        except SmartCategory.DoesNotExist:
            category = ItemCategory.objects.get(slug=slug)
            item_list = []
            item_qs = Item.objects.filter(category=category, in_trash=False, visible=True)
            if item_qs.count() > 0:
                item = {'category': category, 'items': as_matrix(item_qs, self._get_row_len(), strict=True)}
                item_list.append(item)
            context['category'] = category
        else:
            item_list = []
            for category_id in smart_category.items_fk_list:
                category = get_object_or_404(ItemCategory, pk=category_id)
                item_qs = Item.objects.filter(category=category, in_trash=False, visible=True)
                if item_qs.count() > 0:
                    item = {'category': category, 'items':as_matrix(item_qs, self._get_row_len(), strict=True)}
                    item_list.append(item)
            activate_block_title = False
            if len(smart_category.items_fk_list) > 1:
                activate_block_title = True
            context['activate_block_title'] = activate_block_title
            context['smart_category'] = smart_category
        context['item_list'] = item_list
        return context


class FlatPageView(TemplateSelector, TemplateView):
    template_name = 'webnode/flat_page.html'

    def get_context_data(self, **kwargs):
        context = super(FlatPageView, self).get_context_data(**kwargs)
        context['page'] = get_object_or_404(FlatPage, url=kwargs['url'])
        return context


class Registration(TemplateSelector, TemplateView):
    template_name = 'webnode/registration.html'


class appSignIn(TemplateSelector, TemplateView):
    template_name = 'webnode/app_login.html'


def grab_item_list_from_smart_category(smart_category, page):
    item_list = []
    i = 0
    if page == HOME:
        for item_id in smart_category.items_fk_list:
            try:
                item = Item.objects.get(pk=item_id, in_trash=False, visible=True)
            except Item.DoesNotExist:
                pass
            else:
                item_list.append(item)
                i += 1
                if i == 4:
                    break
            smart_category.item_list = item_list
    else:
        for item_id in smart_category.items_fk_list:
            try:
                item = Item.objects.get(pk=item_id, in_trash=False, visible=True)
            except Item.DoesNotExist:
                pass
            else:
                item_list.append(item)
            smart_category.item_list = item_list
    return smart_category


def grab_items_list_from_smart_category(smart_category, page):
    item_list = []
    i = 0
    if page == HOME:
        for category_id in smart_category.items_fk_list:
            try:
                category = ItemCategory.objects.get(pk=category_id)
            except ItemCategory.DoesNotExist:
                pass
            else:
                item_qs = Item.objects.filter(category=category, in_trash=False, visible=True)
                if item_qs.count() > 0:
                    item = {'category': category, 'items': item_qs}
                    item_list.append(item)
                i += 1
                if i == 4:
                    break
            smart_category.item_list = item_list
    else:
        for item_id in smart_category.items_fk_list:
            item = Item.objects.get(pk=item_id)
            item_list.append(item)
        smart_category.item_list = item_list
    return smart_category


def grab_item_list_from_porfolio(smart_category, page):
    item_list = []
    final_item_list = []
    if page == HOME:
        for category_id in smart_category.items_fk_list:
            category = ItemCategory.objects.get(pk=category_id)
            items = Item.objects.filter(category=category, in_trash=False, visible=True)
            for item in items:
                item_list.append(item)
        random.shuffle(item_list)
        if len(item_list) < 4:
            item_list = []
        elif 4 <= len(item_list) < 8:
            item_list = item_list[:4]
        else:
            item_list = item_list[:8]
    else:
        for category_id in smart_category.items_fk_list:
            category = ItemCategory.objects.get(pk=category_id)
            item = Item.objects.filter(category=category, in_trash=False, visible=True)
            for item in item:
                item_list.append(item)
        random.shuffle(item_list)
    return item_list


def get_menus_context():
    categories = {
        'smart_cat_list': SmartCategory.objects.all()
    }
    return categories


class DeployCloud(TemplateView):
    template_name = 'core/cloud_setup/deploy.html'

    def get_context_data(self, **kwargs):
        context = super(DeployCloud, self).get_context_data(**kwargs)
        context['billing_cycles'] = Service.BILLING_CYCLES_CHOICES
        app = Application.objects.using(UMBRELLA).get(slug='webnode')
        context['app'] = app
        template_list = list(Template.objects.using(UMBRELLA).filter(app=app))
        context['theme_list'] = Theme.objects.using(UMBRELLA).filter(template__in=template_list)
        context['can_choose_themes'] = True
        if getattr(settings, 'IS_IKWEN', False):
            billing_plan_list = CloudBillingPlan.objects.using(UMBRELLA).filter(app=app, partner__isnull=True)
            if billing_plan_list.count() == 0:
                setup_months_count = 3
                context['ikwen_setup_cost'] = app.base_monthly_cost * setup_months_count
                context['ikwen_monthly_cost'] = app.base_monthly_cost
                context['setup_months_count'] = setup_months_count
        else:
            service = get_service_instance()
            billing_plan_list = CloudBillingPlan.objects.using(UMBRELLA).filter(app=app, partner=service)
            if billing_plan_list.count() == 0:
                retail_config = ApplicationRetailConfig.objects.using(UMBRELLA).get(app=app, partner=service)
                setup_months_count = 3
                context['ikwen_setup_cost'] = retail_config.ikwen_monthly_cost * setup_months_count
                context['ikwen_monthly_cost'] = retail_config.ikwen_monthly_cost
                context['setup_months_count'] = setup_months_count
        if billing_plan_list.count() > 0:
            context['billing_plan_list'] = billing_plan_list
            context['setup_months_count'] = billing_plan_list[0].setup_months_count
        return context

    def get(self, request, *args, **kwargs):
        member = request.user
        uri = request.META['REQUEST_URI']
        next_url = reverse('ikwen:sign_in') + '?next=' + urlquote(uri)
        if member.is_anonymous():
            return HttpResponseRedirect(next_url)
        if not getattr(settings, 'IS_IKWEN', False):
            if not member.has_perm('accesscontrol.sudo'):
                return HttpResponseForbidden("You are not allowed here. Please login as an administrator.")
        return super(DeployCloud, self).get(request, *args, **kwargs)

    @method_decorator(csrf_protect)
    @method_decorator(never_cache)
    def post(self, request, *args, **kwargs):
        form = DeploymentForm(request.POST)
        if form.is_valid():
            app_id = form.cleaned_data.get('app_id')
            project_name = form.cleaned_data.get('project_name')
            billing_cycle = form.cleaned_data.get('billing_cycle')
            billing_plan_id = form.cleaned_data.get('billing_plan_id')
            domain = form.cleaned_data.get('domain')
            theme_id = form.cleaned_data.get('theme_id')
            partner_id = form.cleaned_data.get('partner_id')
            app = Application.objects.using(UMBRELLA).get(pk=app_id)
            theme = Theme.objects.using(UMBRELLA).get(pk=theme_id)
            billing_plan = CloudBillingPlan.objects.using(UMBRELLA).get(pk=billing_plan_id)

            is_ikwen = getattr(settings, 'IS_IKWEN', False)
            if not is_ikwen or (is_ikwen and request.user.is_staff):
                customer_id = form.cleaned_data.get('customer_id')
                customer = Member.objects.using(UMBRELLA).get(pk=customer_id)
                setup_cost = form.cleaned_data.get('setup_cost')
                monthly_cost = form.cleaned_data.get('monthly_cost')
                if setup_cost < billing_plan.setup_cost:
                    return HttpResponseForbidden("Attempt to set a Setup cost lower than allowed.")
                if monthly_cost < billing_plan.monthly_cost:
                    return HttpResponseForbidden("Attempt to set a monthly cost lower than allowed.")
            else:
                # User self-deploying his website
                customer = Member.objects.using(UMBRELLA).get(pk=request.user.id)
                setup_cost = billing_plan.setup_cost
                monthly_cost = billing_plan.monthly_cost

            partner = Service.objects.using(UMBRELLA).get(pk=partner_id) if partner_id else None
            invoice_entries = []
            domain_name = IkwenInvoiceItem(label='Domain name')
            domain_name_entry = InvoiceEntry(item=domain_name, short_description=domain)
            invoice_entries.append(domain_name_entry)
            website_setup = IkwenInvoiceItem(label='Website setup', price=billing_plan.setup_cost, amount=setup_cost)
            short_description = "Twelve months of service"
            website_setup_entry = InvoiceEntry(item=website_setup, short_description=short_description, total=setup_cost)
            invoice_entries.append(website_setup_entry)
            i = 0
            while True:
                try:
                    label = request.POST['item%d' % i]
                    amount = float(request.POST['amount%d' % i])
                    if not (label and amount):
                        break
                    item = IkwenInvoiceItem(label=label, amount=amount)
                    entry = InvoiceEntry(item=item, total=amount)
                    invoice_entries.append(entry)
                    i += 1
                except:
                    break
            if getattr(settings, 'DEBUG', False):
                service = deploy(app, customer, project_name, billing_plan, theme,
                                 monthly_cost, invoice_entries, billing_cycle, domain, partner_retailer=partner)
            else:
                try:
                    service = deploy(app, customer, project_name, billing_plan, theme,
                                     monthly_cost, invoice_entries, billing_cycle, domain, partner_retailer=partner)
                except Exception as e:
                    context = self.get_context_data(**kwargs)
                    context['error'] = e.message
                    return render(request, 'core/cloud_setup/deploy.html', context)
            if is_ikwen:
                if request.user.is_staff:
                    next_url = reverse('partnership:change_service', args=(service.id, ))
                else:
                    next_url = reverse('ikwen:console')
            else:
                next_url = reverse('change_service', args=(service.id, ))
            return HttpResponseRedirect(next_url)
        else:
            context = self.get_context_data(**kwargs)
            context['form'] = form
            return render(request, 'core/cloud_setup/deploy.html', context)


def rename_webnode_dbs_collections(*args, **kwargs):
    import pymongo

    app = Application.objects.using('umbrella').get(slug='webnode')
    services = Service.objects.using('umbrella').filter(app=app)
    db_connect = pymongo.MongoClient('localhost', 27017)
    dbs = []
    for service in services:
        dbs.append(service.database)

    for db in dbs:
        if db:
            database = db_connect[db]
            try:
                category = database['kakocase_productcategory']
                category.rename('items_itemcategory')
            except:
                pass
            try:
                photo = database['kako_photo']
                photo.rename('items_photo')
            except:
                pass

            try:
                items = database['kako_product']
                items.rename('items_item')
            except:
                pass
            try:
                banner = database['commarketing_banner']
                banner.rename('web_banner')
            except:
                pass
            try:
                homepagesection = database['commarketing_homepagesection']
                homepagesection.rename('web_homepagesection')
            except:
                pass
            try:
                smarcategory = database['commarketing_smartcategory']
                smarcategory.rename('web_smartcategory')
            except:
                pass
        else:
            pass

    return HttpResponse(json.dumps({'Success': True}), 'content-type: text/json')
