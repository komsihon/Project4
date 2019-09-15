import json
import os

from django.conf import settings
from django.contrib import messages
from django.contrib.admin import helpers
from django.contrib.auth.decorators import permission_required
from django.core.files import File
from django.core.urlresolvers import reverse
from django.forms.models import modelform_factory
from django.http import HttpResponse
from django.http.response import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils.decorators import method_decorator
from django.utils.text import slugify
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import TemplateView
from ikwen_kakocase.kakocase.views import SortableListMixin
from ikwen_webnode.items.models import ItemCategory
from ikwen_webnode.web.admin import SmartCategoryAdmin, BannerAdmin, HomepageSectionAdmin
from ikwen_webnode.web.models import Banner, SmartCategory, HomepageSection, SLIDE, FLAT

from ikwen.accesscontrol.templatetags.auth_tokens import append_auth_tokens
from ikwen.core.utils import get_model_admin_instance
from ikwen.core.views import HybridListView, ChangeObjectBase
from ikwen.flatpages.models import FlatPage

BANNER = 'banner'
SMART_CATEGORY = 'smartcategory'


class BannerList(SortableListMixin, TemplateView):
    template_name = 'web/banner_list.html'
    model = Banner
    search_field = 'title'
    ordering = ('-updated_on', )

    def get_context_data(self, **kwargs):
        context = super(BannerList, self).get_context_data(**kwargs)
        context['slide_list'] = Banner.objects.filter(display=SLIDE).order_by('order_of_appearance')
        context['homepage_section_list'] = HomepageSection.objects.all()
        return context


class SmartCategoryList(SortableListMixin, HybridListView):
    template_name = 'web/smart_category_list.html'
    model = SmartCategory
    search_field = 'title'
    ordering = ('order_of_appearance', '-updated_on', )
    context_object_name = 'smart_category_list'


class ChangeSmartObject(TemplateView):
    template_name = 'web/change_smart_object.html'

    def get_context_data(self, **kwargs):
        context = super(ChangeSmartObject, self).get_context_data(**kwargs)
        object_type = kwargs.get('object_type')
        smart_object_id = kwargs.get('smart_object_id')  # May be overridden with the one from GET data
        smart_object_id = self.request.GET.get('smart_object_id', smart_object_id)
        smart_object = None
        if object_type == BANNER:
            model = Banner
            model_admin = BannerAdmin
            fields = ("title", "cta", "target_url",'description',)
        else:
            model = SmartCategory
            model_admin = SmartCategoryAdmin
            fields = ("title", "content_type", "target_url",'description',)
        if smart_object_id:
            smart_object = get_object_or_404(model, pk=smart_object_id)
            smart_object.content = [ItemCategory.objects.get(pk=pk) for pk in smart_object.items_fk_list]
        object_admin = get_model_admin_instance(model, model_admin)
        ModelForm = modelform_factory(model, fields=fields)
        form = ModelForm(instance=smart_object)
        model_admin_form = helpers.AdminForm(form, list(object_admin.get_fieldsets(self.request)),
                                             object_admin.get_prepopulated_fields(self.request))
        context['page_list'] = FlatPage.objects.all()
        context['object_type'] = object_type
        context['smart_object'] = smart_object
        context['model_admin_form'] = model_admin_form
        return context

    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    def post(self, request, *args, **kwargs):
        object_type = kwargs.get('object_type')
        smart_object_id = request.POST['smart_object_id']
        smart_object = None
        if object_type == BANNER:
            model = Banner
            model_admin = BannerAdmin
        else:
            model = SmartCategory
            model_admin = SmartCategoryAdmin
        if smart_object_id:
            smart_object = get_object_or_404(model, pk=smart_object_id)
        category_admin = get_model_admin_instance(model, model_admin)
        ModelForm = category_admin.get_form(self.request)
        form = ModelForm(request.POST, instance=smart_object)
        if form.is_valid():
            title = form.cleaned_data['title']
            slug = slugify(title)
            content_type = form.cleaned_data.get('content_type', 'Slide')
            if content_type == 'FlatPage':
                description = request.POST['page_url']
            else:
                description = form.cleaned_data.get('description')
            badge_text = form.cleaned_data.get('badge_text')
            order = form.cleaned_data.get('order_of_appearance')
            display = form.cleaned_data.get('display')
            image_url = request.POST.get('image_url')
            target_url = request.POST.get('target_url')
            cta = request.POST.get('cta')
            if not smart_object:
                smart_object = model()
            smart_object.title = title
            smart_object.content_type = content_type
            smart_object.slug = slug
            if description:
                smart_object.description = description
            if badge_text:
                smart_object.badge_text = badge_text
            if order:
                smart_object.order_of_appearance = order
            if display:
                smart_object.display = display
            if cta:
                smart_object.cta = cta
            if target_url:
                smart_object.target_url = target_url
            smart_object.save()
            if object_type == BANNER:
                pass
            else:
                try:
                    ItemCategory.objects.get(slug=slug)
                except ItemCategory.DoesNotExist:
                    item_category = ItemCategory(name=title, slug=slug)
                    item_category.save()
                    smart_object.items_fk_list.append(item_category.id)
                    smart_object.save()
                else:
                    pass

            if image_url:
                if not smart_object.image.name or image_url != smart_object.image.url:
                    filename = image_url.split('/')[-1]
                    media_root = getattr(settings, 'MEDIA_ROOT')
                    media_url = getattr(settings, 'MEDIA_URL')
                    image_url = image_url.replace(media_url, '')
                    try:
                        with open(media_root + image_url, 'r') as f:
                            content = File(f)
                            destination = media_root + SmartCategory.UPLOAD_TO + "/" + filename
                            smart_object.image.save(destination, content)
                        os.unlink(media_root + image_url)
                    except IOError as e:
                        if getattr(settings, 'DEBUG', False):
                            raise e
                        return {'error': 'File failed to upload. May be invalid or corrupted image file'}
            if smart_object_id:
                next_url = reverse('web:change_smart_object', args=(object_type, smart_object_id, ))
                messages.success(request, _("Category %s successfully updated." % smart_object.title))
            else:
                next_url = reverse('web:change_smart_object', args=(object_type, ))
                messages.success(request, _("Category %s successfully created." % smart_object.title))
            next_url = append_auth_tokens(next_url, request)
            return HttpResponseRedirect(next_url)
        else:
            context = self.get_context_data(**kwargs)
            context['errors'] = form.errors
            return render(request, self.template_name, context)


class ChangeHomepageSection(ChangeObjectBase):
    model = HomepageSection
    model_admin = HomepageSectionAdmin
    context_object_name = 'smart_object'
    template_name = 'web/change_homepage_section.html'

    def post(self, request, *args, **kwargs):
        object_id = kwargs.get('object_id')
        smart_object = None
        if object_id:
            smart_object = get_object_or_404(HomepageSection, pk=object_id)
        model_admin = get_model_admin_instance(HomepageSection, self.model_admin)
        ModelForm = model_admin.get_form(self.request)
        form = ModelForm(request.POST, instance=smart_object)
        if form.is_valid():
            title = form.cleaned_data['title']
            slug = slugify(title)
            content_type = form.cleaned_data['content_type']
            density = request.POST.get('density')
            image_url = request.POST.get('image_url')
            if not smart_object:
                smart_object = HomepageSection()
            smart_object.title = title
            smart_object.slug = slug
            smart_object.density = density
            smart_object.content_type = content_type
            if content_type == FLAT:
                smart_object.description = form.cleaned_data['description']
            else:
                smart_object.description = request.POST['menu']
            smart_object.text_position = form.cleaned_data['text_position']
            smart_object.cta = form.cleaned_data['cta']
            smart_object.target_url = form.cleaned_data['target_url']
            smart_object.background_image = True if request.POST.get('background_image') else False
            smart_object.save()

            if image_url:
                if not smart_object.image.name or image_url != smart_object.image.url:
                    filename = image_url.split('/')[-1]
                    media_root = getattr(settings, 'MEDIA_ROOT')
                    media_url = getattr(settings, 'MEDIA_URL')
                    image_url = image_url.replace(media_url, '')
                    try:
                        with open(media_root + image_url, 'r') as f:
                            content = File(f)
                            destination = media_root + SmartCategory.UPLOAD_TO + "/" + filename
                            smart_object.image.save(destination, content)
                        os.unlink(media_root + image_url)
                    except IOError as e:
                        if getattr(settings, 'DEBUG', False):
                            raise e
                        return {'error': 'File failed to upload. May be invalid or corrupted image file'}
            if object_id:
                next_url = reverse('web:change_homepage_section', args=(object_id, ))
                messages.success(request, _("Section %s successfully updated." % smart_object.title))
            else:
                next_url = reverse('web:change_homepage_section')
                messages.success(request, _("Section %s successfully created." % smart_object.title))
            return HttpResponseRedirect(next_url)
        else:
            context = self.get_context_data(**kwargs)
            context['errors'] = form.errors
            return render(request, self.template_name, context)


@permission_required('web.ik_manage_marketing')
def set_smart_object_content(request, action, *args, **kwargs):
    smart_object_id = request.GET['smart_object_id']
    selection = request.GET['selection'].split(',')
    try:
        smart_object = Banner.objects.get(pk=smart_object_id)
        next_url = reverse('web:change_smart_object', args=(BANNER, smart_object_id, ))
        messages.success(request, _("Banner %s successfully saved." % smart_object.title))
    except Banner.DoesNotExist:
        smart_object = get_object_or_404(SmartCategory, pk=smart_object_id)
        next_url = reverse('web:change_smart_object', args=(SMART_CATEGORY, smart_object_id, ))
        messages.success(request, _("Smart Category %s successfully saved." % smart_object.title))
    if action == 'add':
        smart_object.items_fk_list = selection
        response = HttpResponseRedirect(next_url)
    elif action == 'remove':
        deleted = []
        for pk in selection:
            try:
                smart_object.items_fk_list.remove(pk)
                deleted.append(pk)
            except ValueError:
                pass
        message = "%d item(s) deleted." % len(deleted)
        response = HttpResponse(json.dumps({'message': message, 'deleted': deleted}), 'content-type: text/json')
    smart_object.items_count = len(smart_object.items_fk_list)
    smart_object.save()
    return response


@permission_required('web.ik_manage_marketing')
def toggle_smart_object_attribute(request, *args, **kwargs):
    object_id = request.GET['object_id']
    attr = request.GET['attr']
    val = request.GET['val']
    try:
        obj = SmartCategory.objects.get(pk=object_id)
    except SmartCategory.DoesNotExist:
        try:
            obj = Banner.objects.get(pk=object_id)
        except Banner.DoesNotExist:
            obj = HomepageSection.objects.get(pk=object_id)
    if val.lower() == 'true':
        obj.__dict__[attr] = True
    else:
        obj.__dict__[attr] = False
    obj.save()
    response = {'success': True}
    return HttpResponse(json.dumps(response), 'content-type: text/json')


@permission_required('web.ik_manage_marketing')
def delete_smart_object(request, *args, **kwargs):
    selection = request.GET['selection'].split(',')
    deleted = []
    for pk in selection:
        try:
            Banner.objects.get(pk=pk).delete()
            deleted.append(pk)
        except Banner.DoesNotExist:
            try:
                menu = SmartCategory.objects.get(pk=pk)
                try:
                    ItemCategory.objects.get(slug=menu.slug).delete()
                except ItemCategory.DoesNotExist:
                    pass
                menu.delete()
                deleted.append(pk)
            except SmartCategory.DoesNotExist:
                try:
                    HomepageSection.objects.get(pk=pk).delete()
                    deleted.append(pk)
                except HomepageSection.DoesNotExist:
                    message = "Object %s was not found." % pk
                    break
    else:
        message = "%d item(s) deleted." % len(deleted)
    response = {'message': message, 'deleted': deleted}
    return HttpResponse(json.dumps(response), 'content-type: text/json')
