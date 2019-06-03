#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ikwen.conf.settings")

from ikwen.core.models import Service, Application

import logging.handlers
error_log = logging.getLogger('rename_webnode_dbs_collections.error')
error_log.setLevel(logging.ERROR)
error_file_handler = logging.handlers.RotatingFileHandler('rename_dbs.log', 'w', 1000000, 4)
error_file_handler.setLevel(logging.INFO)
error_log.addHandler(error_file_handler)


def rename_webnode_dbs_collections(*args, **kwargs):
    import pymongo

    app = Application.objects.using('umbrella').get(slug='webnode')
    services = Service.objects.using('umbrella').filter(app=app)
    db_connect = pymongo.MongoClient('46.101.107.75', 27017)
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


if __name__ == "__main__":
    try:
        rename_webnode_dbs_collections()
    except:
        error_log.error(u"Fatal error occured", exc_info=True)
