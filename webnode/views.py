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

from ikwen_webnode.commarketing.models import Banner, SmartCategory, SLIDE, FULL_WIDTH_SECTION, HomepageSection
from ikwen.core.views import BaseView
from ikwen_kakocase.kako.models import Product
from ikwen_kakocase.kakocase.models import ProductCategory
import random


from ikwen_webnode.blog.models import Post
from ikwen_webnode.blog.views import WebNodeBaseView

from conf import settings
from ikwen_webnode.webnode.cloud_setup import deploy, DeploymentForm

HOME = 'home'
POST_PER_PAGE = 5


class TemplateSelector(object):
    def get_template_names(self):
        s = get_service_instance()
        tokens = self.template_name.split('/')
        if s.project_name_slug == 'improve':
            tokens.insert(1, 'improve')
        return ['/'.join(tokens)]


class Home(TemplateSelector, WebNodeBaseView):
    template_name = 'webnode/home.html'

    def get_context_data(self, **kwargs):
        context = super(Home, self).get_context_data(**kwargs)
        smart_objects = SmartCategory.objects.filter(appear_in_menu=True).exclude(pk=settings.PORTFOLIO_ID).exclude(pk=settings.PARTNER_ID).exclude(pk=settings.HOME_ID)
        partners_smart_objects = SmartCategory.objects.filter(appear_in_menu=True, pk=settings.PARTNER_ID)
        home_entry_list, partner_list = [], []
        for smart_object in smart_objects:
            item_list = grab_items_list_from_smart_category(smart_object, HOME)
            home_entry_list.append(item_list)


        for smart_objects in partners_smart_objects:
            for category in smart_objects.items_fk_list:
                partners_category = ProductCategory.objects.get(pk=category)
                partner_list = Product.objects.filter(category=partners_category)

        try:
            SmartCategory.objects.get(pk=settings.PORTFOLIO_ID)
        except SmartCategory.DoesNotExist:
            pass
        else:
            smart_portfolio = SmartCategory.objects.get(pk=settings.PORTFOLIO_ID)
            smart_portfolio_items = grab_product_list_from_porfolio(smart_portfolio, HOME)
            context['smart_portfolio_items'] = smart_portfolio_items
            context['smart_portfolio'] = smart_portfolio

        posts = Post.objects.filter(publish=True)
        post_list = []
        for post in posts:
            post_list.append(post)
        random.shuffle(post_list)
        entries = post_list[:4]
        context['entries'] = entries
        context['slideshow'] = Banner.objects.filter(display=SLIDE, is_active=True).order_by('order_of_appearance')
        context['services'] = Banner.objects.filter(display=SLIDE, is_active=True).order_by('-id')
        context['homepage_section_list'] = HomepageSection.objects.filter(is_active=True).order_by('order_of_appearance')

        context['home_entry_list'] = home_entry_list[:4]
        context['partners_list'] = partner_list
        # context['sm_services'] = services
        return context


class AdminHome(BaseView):
    template_name = 'admin_home.html'


class ProductDetails(TemplateSelector, WebNodeBaseView):
    template_name = 'webnode/detail.html'

    def get_context_data(self, **kwargs):
        context = super(ProductDetails, self).get_context_data(**kwargs)
        slug = kwargs['slug']
        product = Product.objects.get(slug=slug)
        category = product.category
        items_qs = Product.objects.filter(category=category)
        suggestions =[]
        for item in items_qs:
            if item != product:
                suggestions.append(item)
        random.shuffle(suggestions)
        context['product'] = product
        context['suggestions'] = suggestions[:4]
        return context


class Portfolio(TemplateSelector, WebNodeBaseView):
    template_name = 'webnode/portfolio.html'

    def get_context_data(self, **kwargs):
        context = super(Portfolio, self).get_context_data(**kwargs)
        category_list = []
        smart_portfolio = SmartCategory.objects.get( pk=settings.PORTFOLIO_ID)
        smartPortfolio = grab_product_list_from_porfolio(smart_portfolio, None)
        context['smart_portfolio'] = smartPortfolio
        for category_id in smart_portfolio.items_fk_list:
            category = ProductCategory.objects.get(pk=category_id)
            items_Count = Product.objects.filter(category=category).count()
            if items_Count > 0:
                category_list.append(category)
        context['category_list'] = category_list
        return context


class ItemList(TemplateSelector, WebNodeBaseView):
    template_name = 'webnode/item_list.html'

    def get_context_data(self, **kwargs):
        context = super(ItemList, self).get_context_data(**kwargs)
        slug = kwargs['slug']
        smart_category = SmartCategory.objects.get(slug=slug)
        item_list = []
        for category_id in smart_category.items_fk_list:
            category = ProductCategory.objects.get(pk=category_id)
            item_qs = Product.objects.filter(category=category)
            if item_qs.count() > 0:
                item = {'category': category, 'items':item_qs}
                item_list.append(item)
        activate_block_title = False
        if len(smart_category.items_fk_list) > 1:
            activate_block_title = True
        context['item_list'] = item_list
        context['smart_category'] = smart_category
        context['activate_block_title'] = activate_block_title
        # context['partners'] = Banner.objects.filter(display=partners_category)[:5]
        return context


class FlatPageView(TemplateSelector, WebNodeBaseView):
    template_name = 'webnode/about.html'

    def get_context_data(self, **kwargs):
        context = super(FlatPageView, self).get_context_data(**kwargs)
        context['page'] = get_object_or_404(FlatPage, url=kwargs['url'])
        return context


def grab_product_list_from_smart_category(smart_category, page):
    product_list = []
    i = 0
    if page == HOME:
        for product_id in smart_category.items_fk_list:
            try:
                product = Product.objects.get(pk=product_id)
            except Product.DoesNotExist:
                pass
            else:
                product_list.append(product)
                i += 1
                if i == 4:
                    break
            smart_category.product_list = product_list
    else:
        for product_id in smart_category.items_fk_list:
            product = Product.objects.get(pk=product_id)
            product_list.append(product)
        smart_category.product_list = product_list
    return smart_category


def grab_items_list_from_smart_category(smart_category, page):
    product_list = []
    i = 0
    if page == HOME:
        for category_id in smart_category.items_fk_list:
            try:
                category = ProductCategory.objects.get(pk=category_id)
            except ProductCategory.DoesNotExist:
                pass
            else:
                item_qs = Product.objects.filter(category=category)
                if item_qs.count() > 0:
                    item = {'category': category, 'items': item_qs}
                    product_list.append(item)
                i += 1
                if i == 4:
                    break
            smart_category.product_list = product_list
    else:
        for product_id in smart_category.items_fk_list:
            product = Product.objects.get(pk=product_id)
            product_list.append(product)
        smart_category.product_list = product_list
    return smart_category


def grab_product_list_from_porfolio(smart_category, page):
    product_list = []
    final_product_list = []
    if page == HOME:
        for category_id in smart_category.items_fk_list:
            category = ProductCategory.objects.get(pk=category_id)
            products = Product.objects.filter(category=category)
            for product in products:
                product_list.append(product)
        random.shuffle(product_list)
        if len(product_list) < 4:
            product_list = []
        elif 4 <= len(product_list) < 8:
            product_list = product_list[:4]
        else:
            product_list = product_list[:8]
    else:
        for category_id in smart_category.items_fk_list:
            category = ProductCategory.objects.get(pk=category_id)
            product = Product.objects.filter(category=category)
            for product in product:
                product_list.append(product)
        random.shuffle(product_list)
    return product_list


def get_menus_context():
    categories = {
        'smart_cat_list': SmartCategory.objects.all().exclude(pk=settings.HOME_ID)
    }
    return categories


class DeployCloud(BaseView):
    template_name = 'core/cloud_setup/deploy.html'

    def get_context_data(self, **kwargs):
        context = super(DeployCloud, self).get_context_data(**kwargs)
        context['billing_cycles'] = Service.BILLING_CYCLES_CHOICES
        app_slug = kwargs['app_slug']
        app = Application.objects.using(UMBRELLA).get(slug=app_slug)
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
