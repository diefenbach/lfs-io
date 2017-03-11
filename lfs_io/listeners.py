import logging

from django.db.models.signals import pre_delete
from django.dispatch import receiver

from lfs.catalog.models import Product

logger = logging.getLogger(__name__)


@receiver(pre_delete, sender=Product)
def log_deleted_product(sender, instance, using, **kwargs):
    logger.info("Product deleted {}".format(instance.uid))
