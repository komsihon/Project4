import json
import os
from datetime import datetime

import tablib
from ajaxuploader.views import AjaxFileUploader
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.core.files import File
from django.http import HttpResponse
from django.utils import timezone
from ikwen.core.models import Service

from ikwen.accesscontrol.backends import UMBRELLA
from ikwen.core.utils import DefaultUploadBackend, get_service_instance, add_database_to_settings
from ikwen_webnode.items.admin import ItemResource
from ikwen_kakocase.kakocase.models import OperatorProfile
from ikwen_webnode.items.models import Item, BatchUpload
from ikwen_webnode.webnode.models import PROVIDER_ADDED_ITEMS_EVENT


class ItemSpreadsheetUploadBackend(DefaultUploadBackend):
    """
    Ajax spreadsheet upload handler for :class:`items.models.BatchUpload`
    """
    def upload_complete(self, request, filename, *args, **kwargs):
        path = self.UPLOAD_DIR + "/" + filename
        self._dest.close()
        media_root = getattr(settings, 'MEDIA_ROOT')
        try:
            with open(media_root + path, 'r') as f:
                content = File(f)
                destination = media_root + BatchUpload.UPLOAD_TO + "/" + filename
                batch_upload = BatchUpload()
                batch_upload.spreadsheet.save(destination, content)
                service = get_service_instance()
                item_resource = ItemResource()
                item_resource.provider = service
                item_resource.retail_price_is_modifiable = True if request.GET.get('retail_price_is_modifiable') else False
                dataset = tablib.Dataset()
                dataset.xls = open(destination).read()
                col_id = ['' for i in range(dataset.height)]
                dataset.insert_col(0, col_id, header='id')
                try:
                    result = item_resource.import_data(dataset, dry_run=True)
                    result.has_errors()
                except Exception as e:
                    return {
                        'exception': e.message
                    }
            os.unlink(media_root + path)
            return {
                'id': batch_upload.id,
                'url': batch_upload.image.thumb_url
            }
        except IOError as e:
            if settings.DEBUG:
                raise e
            return {'error': 'File failed to upload. May be invalid or corrupted image file'}


item_batch_uploader = AjaxFileUploader(ItemSpreadsheetUploadBackend)


@permission_required('items.manage_item')
def do_import_items_from_spreadsheet(request, *args, **kwargs):
    upload_id = request.GET['upload_id']
    upload = BatchUpload.objects.get(pk=upload_id)

    service = get_service_instance()
    item_resource = ItemResource()
    item_resource.provider = service
    item_resource.batch_upload = upload
    item_resource.retail_price_is_modifiable = True if request.GET.get('retail_price_is_modifiable') else False
    dataset = tablib.Dataset()
    dataset.xls = open(upload.spreadsheet.path).read()
    col_id = ['' for i in range(dataset.height)]
    dataset.insert_col(0, col_id, header='id')
    item_resource.import_data(dataset, dry_run=False)

    # TODO: Think more on this event as it may appear on retailer's console without images being uploaded
    # if getattr(settings, 'IS_PROVIDER', False):
    #     for retailer in OperatorProfile.objects.filter(business_type=OperatorProfile.RETAILER):
    #         member = retailer.service.member
    #         db = retailer.service.database
    #         add_database_to_settings(db)
    #         add_event(retailer.service, member, PROVIDER_ADDED_ITEMS_EVENT, upload_id)
    response = {'success': True}
    return HttpResponse(json.dumps(response), 'content-type: text/json')


def set_stock(request, api_signature, ref, units, *args, **kwargs):
    units = float(units)
    update_method = OperatorProfile.AUTO_UPDATE
    service = get_service_instance()
    config = service.config
    if service.api_signature != api_signature:
        response = {'error': "Invalide API Signature."}
        return HttpResponse(json.dumps(response), 'content-type: text/json')
    try:
        item = Item.objects.get(reference=ref)
    except Item.DoesNotExist:
        try:
            item = Item.objects.get(pk=ref)
        except Item.DoesNotExist:
            response = {'error': "No item found with reference '%s'." % ref}
            return HttpResponse(json.dumps(response), 'content-type: text/json')
    warning = None
    item.stock = units
    item.save()
    for retailer in OperatorProfile.objects.filter(business_type=OperatorProfile.RETAILER):
        db = retailer.service.database
        add_database_to_settings(db)
        Item.objects.using(db).filter(pk=item.id).update(stock=units)

    OperatorProfile.objects.using(UMBRELLA).filter(pk=config.id).update(stock_updated_on=datetime.now(),
                                                                        last_stock_update_method=update_method)

    response = {
        'success': True,
        'details': {
            'kcid': item.id,
            'stock': item.stock
        }
    }
    if warning:
        response['warning'] = warning
    return HttpResponse(json.dumps(response), 'content-type: text/json')
