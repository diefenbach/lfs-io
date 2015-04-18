# Python imports
import json
import re
import StringIO
import zipfile

# django imports
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.http import HttpResponse

# lfs imports
from lfs.catalog.models import GroupsPropertiesRelation
from lfs.catalog.models import Product
from lfs.catalog.models import ProductAccessories
from lfs.catalog.models import ProductsPropertiesRelation
from lfs.catalog.models import ProductPropertyValue
from lfs.catalog.models import Property
from lfs.catalog.models import PropertyOption
from lfs.catalog.settings import PROPERTY_SELECT_FIELD
from lfs.export.utils import register


# Load logger
import logging
logger = logging.getLogger("default")


def export(request, export):
    """Generic export method.
    """
    buffer = StringIO.StringIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        result = []
        for product in export.get_products():
            # Images
            images = []
            for image in product.images.all():
                images.append({
                    "path": image.image.name,
                    "name": image.image.name.split("/")[-1],
                    "title": image.title,
                    "position": image.position,
                })
                zf.write(image.image.file.name, image.image.name)

            # Attachments
            attachments = []
            for attachment in product.attachments.all():
                attachments.append({
                    "path": attachment.file.name,
                    "name": attachment.file.name.split("/")[-1],
                    "title": attachment.title,
                    "description": attachment.description,
                    "position": attachment.position,

                })
                zf.write(attachment.file.file.name, attachment.file.name)

            # Accessories
            accessories = []
            for accessory in ProductAccessories.objects.filter(product=product):
                accessories.append({
                    "uid": accessory.accessory.uid,
                    "position": accessory.position,
                    "quantity": accessory.quantity,
                })

            related_products = [r.uid for r in product.related_products.all()]
            parent = product.parent.uid if product.parent else ""
            tax = product.tax.rate if product.tax else ""
            price_calculator = product.price_calculator.id if product.price_calculator else ""
            manufacturer = product.manufacturer.name if product.manufacturer else ""
            default_variant = product.default_variant.uid if product.default_variant else ""
            ordered_at = str(product.ordered_at) if product.ordered_at else ""

            # price calculation
            def replace_id(match):
                try:
                    prop = Property.objects.get(pk=match.groups()[0])
                except Property.DoesNotExist:
                    return "property({})".format(match.groups()[0])
                else:
                    return "property({})".format(prop.uid)
            price_calculation = re.sub(r"property\((\d+)\)", replace_id, product.price_calculation)

            # Category variant
            if product.category_variant and (product.category_variant < 0):
                category_variant = product.category_variant
            else:
                try:
                    variant = Product.objects.get(pk=product.category_variant)
                    category_variant = variant.uid
                except Product.DoesNotExist:
                    category_variant = None

            # Local properties (atm only local properties have an ProductsPropertiesRelation)
            local_properties = []
            for ppr in ProductsPropertiesRelation.objects.filter(product=product):
                options = []
                for option in ppr.property.options.all():
                    options.append({
                        "uid": option.uid,
                        "name": option.name,
                        "price": option.price,
                        "position": option.position,
                    })
                local_properties.append({
                    "uid": ppr.property.uid,
                    "name": ppr.property.name,
                    "position": ppr.position,
                    "local": ppr.property.local,
                    "options": options,
                })

            # Property groups and global properties
            property_groups = []
            for property_group in product.property_groups.all():
                properties = []
                for gpr in GroupsPropertiesRelation.objects.filter(group=property_group):
                    options = []
                    for option in gpr.property.options.all():
                        options.append({
                            "uid": option.uid,
                            "name": option.name,
                            "price": option.price,
                            "position": option.position,
                        })
                    steps = []
                    for step in gpr.property.steps.all():
                        steps.append({
                            "start": step.start,
                        })

                    # LFS < 0.8 has no property.variants attribute
                    try:
                        variants = gpr.property.variants
                    except AttributeError:
                        variants = True

                    properties.append({
                        "uid": gpr.property.uid,
                        "name": gpr.property.name,
                        "title": gpr.property.title,
                        "type": gpr.property.type,
                        "position": gpr.property.position,
                        "group_position": gpr.position,
                        "local": gpr.property.local,
                        "unit": gpr.property.unit,
                        "display_on_product": gpr.property.display_on_product,
                        "variants": variants,
                        "filterable": gpr.property.filterable,
                        "configurable": gpr.property.configurable,
                        "type": gpr.property.type,
                        "price": gpr.property.price,
                        "display_price": gpr.property.display_price,
                        "add_price": gpr.property.add_price,
                        "unit_min": gpr.property.unit_min,
                        "unit_max": gpr.property.unit_max,
                        "unit_step": gpr.property.unit_step,
                        "decimal_places": gpr.property.decimal_places,
                        "required": gpr.property.required,
                        "step_type": gpr.property.step_type,
                        "step": gpr.property.step,
                        "options": options,
                        "steps": steps,
                    })
                try:
                    position = property_group.position
                except AttributeError:
                    position = 10

                property_groups.append({
                    "uid": property_group.uid,
                    "name": property_group.name,
                    "position": position,
                    "properties": properties,
                })

            # Property values (local and global)
            property_values = []
            for ppv in ProductPropertyValue.objects.filter(product=product):
                parent_temp = Product.objects.get(pk=ppv.parent_id)
                if ppv.property.local or (ppv.property.type == PROPERTY_SELECT_FIELD):
                    option_temp = PropertyOption.objects.get(pk=ppv.value)
                    value = option_temp.uid
                else:
                    value = ppv.value

                # NOTE: Property in LFS 0.8 has no group attribute
                property_values.append({
                    "product": product.uid,
                    "property": ppv.property.uid,
                    "local": ppv.property.local,
                    "parent": parent_temp.uid,
                    "value": value,
                    "value_as_float": ppv.value_as_float,
                    "type": ppv.type,
                })

            # Delivery time
            if product.delivery_time:
                delivery_time = {
                    "min": product.delivery_time.min,
                    "max": product.delivery_time.max,
                    "unit": product.delivery_time.unit,
                    "description": product.delivery_time.description,
                }
            else:
                delivery_time = None

            result.append({
                "uid": product.uid,
                "name": product.name,
                "sku": product.sku,
                "slug": product.slug,
                "price": product.price,
                "effective_price": product.effective_price,
                "price_unit": product.price_unit,
                "unit": product.unit,
                "short_description": product.short_description,
                "description": product.description,
                "meta_title": product.meta_title,
                "meta_keywords": product.meta_keywords,
                "meta_description": product.meta_description,
                "for_sale": product.for_sale,
                "for_sale_price": product.for_sale_price,
                "active": product.active,
                "creation_date": str(product.creation_date),
                "supplier": product.supplier,
                "deliverable": product.deliverable,
                "manual_delivery_time": product.manual_delivery_time,
                "delivery_time": delivery_time,
                "order_time": product.order_time,
                "ordered_at": ordered_at,
                "manage_stock_amount": product.manage_stock_amount,
                "stock_amount": product.stock_amount,
                "active_packing_unit": product.active_packing_unit,
                "packing_unit": product.packing_unit,
                "packing_unit_unit": product.packing_unit_unit,
                "weight": product.weight,
                "height": product.height,
                "length": product.length,
                "width": product.width,
                "tax": tax,
                "sub_type": product.sub_type,
                "default_variant": default_variant,
                "category_variant": category_variant,
                "variants_display_type": product.variants_display_type,
                "variant_position": product.variant_position,
                "parent": parent,
                "active_name": product.active_name,
                "active_sku": product.active_sku,
                "active_short_description": product.active_short_description,
                "active_static_block": product.active_static_block,
                "active_description": product.active_description,
                "active_price": product.active_price,
                "active_for_sale": product.active_for_sale,
                "active_for_sale_price": product.active_for_sale_price,
                "active_images": product.active_images,
                "active_related_products": product.active_related_products,
                "active_accessories": product.active_accessories,
                "active_meta_title": product.active_meta_title,
                "active_meta_description": product.active_meta_description,
                "active_meta_keywords": product.active_meta_keywords,
                "active_dimensions": product.active_meta_keywords,
                "template": product.template,
                "price_calculator": price_calculator,
                "active_price_calculation": product.active_price_calculation,
                "price_calculation": price_calculation,
                "active_base_price": product.active_base_price,
                "base_price_unit": product.base_price_unit,
                "base_price_amount": product.base_price_amount,
                "sku_manufacturer": product.sku_manufacturer,
                "manufacturer": manufacturer,
                "type_of_quantity_field": product.type_of_quantity_field,
                "uid": product.uid,
                "related_products": related_products,
                "accessories": accessories,
                "images": images,
                "attachments": attachments,
                "local_properties": local_properties,
                "property_values": property_values,
                "property_groups": property_groups,
            })
        zf.writestr("data.json", json.dumps(result))

    response = HttpResponse(buffer.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = "attachment; filename=%s.zip" % export.name
    return response

register(export, "io")


@receiver(pre_delete, sender=Product)
def log_deleted_product(sender, instance, using, **kwargs):
    logger.info("Product deleted {}".format(instance.uid))
