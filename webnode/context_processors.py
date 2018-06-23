from ikwen.flatpages.models import FlatPage
from ikwen_webnode.items.models import ItemCategory
from ikwen_webnode.web.models import SmartCategory
from ikwen_kakocase.kakocase.context_processors import project_settings as kakocase_settings

def project_settings(request):
    """
    Adds utility project url and ikwen base url context variable to the context.
    """
    webnode_settings = kakocase_settings(request)
    webnode_settings['settings']['IS_WEBNODE'] = True
    return webnode_settings


def menu_list(request):
    return {
                'menu_list': SmartCategory.objects.filter(is_active=True).order_by('order_of_appearance'),
                'flat_pages':  FlatPage.objects.all()
            }
