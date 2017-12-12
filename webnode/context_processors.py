from django.conf import settings
from ikwen_kakocase.commarketing.models import SmartCategory
from ikwen_kakocase.kakocase.context_processors import project_settings as kakocase_settings


def project_settings(request):
    """
    Adds utility project url and ikwen base url context variable to the context.
    """
    webnode_settings = kakocase_settings(request)['settings']
    webnode_settings.update({
        'IS_WEBNODE': True,
    })
    return {
        'settings': webnode_settings
    }


def get_menu_list(request):
    Home_link_id = getattr(settings, 'HOME_ID', None)
    webnode_menu = SmartCategory.objects.filter(is_active=True).exclude(pk=Home_link_id).order_by('title')
    menu_list = []
    for menu in webnode_menu:
        nav = {
            'menu': menu,
            'category_list': menu.get_category_queryset()
        }
        menu_list.append(nav)
    return {'smart_cat_list': menu_list}