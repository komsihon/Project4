#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ikwen.conf.settings")


from ikwen.core.models import *
from ikwen.core.utils import *
from ikwen_webnode.items.models import *


app = Application.objects.get(slug='kakocase')
for s in Service.objects.filter(app=app):
    db = s.database
    add_database(s.database)
    for item in Item.objects.using(db):
        slug = slugify(item.name)
        category = item.category
        try:
            Item.objects.using(db).filter(category=category, slug=slug)[0]
            if item.size:
                slug += '-' + slugify(item.size)
            Item.objects.using(db).filter(category=category, slug=slug)[0]
            pname = slug
            i = 1
            while True:
                try:
                    i += 1
                    pname = "%s-%d" % (slug, i)
                    Item.objects.using(db).filter(category=category, slug=pname)[0]
                except ValueError:
                    slug = pname
                    break
        except IndexError:
            pass
        item.slug = slug
        item.save(using=db)
