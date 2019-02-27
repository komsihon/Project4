from django.db import models

from ikwen.billing.models import Donation
from ikwen.core.models import Model
from django.utils.translation import gettext_lazy as _
from ikwen.accesscontrol.models import Member


class Bounty(Model):
    PENDING = 'Pending'
    PAID = 'Paid'

    STATUS_CHOICES = (
        (PENDING, _('Pending')),
        (PAID, _('Paid')),
    )
    amount = models.IntegerField(blank=False, unique=True)
    member = models.ForeignKey(Member, blank=True, null=True)
    donation = models.ForeignKey(Donation, blank=True, null=True)
    status = models.BooleanField(default=PENDING)

    def __unicode__(self):
        return "%s" % self.name