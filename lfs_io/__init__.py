# Python imports
import json
import zipfile
import StringIO

# django imports
from django.core.files.base import ContentFile
from django.http import HttpResponse

# lfs imports
from lfs.catalog.models import FilterStep
from lfs.catalog.models import GroupsPropertiesRelation
from lfs.catalog.models import Image
from lfs.catalog.models import Product
from lfs.catalog.models import ProductAccessories
from lfs.catalog.models import ProductAttachment
from lfs.catalog.models import ProductsPropertiesRelation
from lfs.catalog.models import ProductPropertyValue
from lfs.catalog.models import Property
from lfs.catalog.models import PropertyGroup
from lfs.catalog.models import PropertyOption
from lfs.catalog.models import Tax
from lfs.catalog.settings import PROPERTY_SELECT_FIELD
from lfs.export.utils import register
from lfs.manufacturer.models import Manufacturer

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

            # Category variant
            if product.category_variant and (product.category_variant < 0):
                category_variant = product.category_variant
            else:
                try:
                    variant = Product.objects.get(pk=product.category_variant)
                    category_variant = variant.uid
                except Product.DoesNotExist:
                    category_variant = None

            # Local properties
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

            # Property values
            property_values = []
            for ppv in ProductPropertyValue.objects.filter(product=product):
                parent_temp = Product.objects.get(pk=ppv.parent_id)
                if ppv.property.local or (ppv.property.type == PROPERTY_SELECT_FIELD):
                    option_temp = PropertyOption.objects.get(pk=ppv.value)
                    value = option_temp.uid
                else:
                    value = ppv.value

                property_values.append({
                    "property": ppv.property.uid,
                    "local": ppv.property.local,
                    "parent": parent_temp.uid,
                    "property_group": ppv.property_group.uid,
                    "value": value,
                    "value_as_float": ppv.value_as_float,
                    "type": ppv.type,
                })

            # Property groups
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
                        "variants": gpr.property.variants,
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
                property_groups.append({
                    "uid": property_group.uid,
                    "name": property_group.name,
                    "position": property_group.position,
                    "properties": properties,
                })

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
                "delivery_time": product.delivery_time,
                "order_time": product.order_time,
                "ordered_at": ordered_at,
                "manage_stock_amount": product.manage_stock_amount,
                "stock_amount": product.stock_amount,
                "active_packing_unit": product.active_packing_unit,
                "packing_unit": product.packing_unit,
                "packing_unit_unit": product.packing_unit_unit,
                "static_block": product.static_block,
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
                "price_calculation": product.price_calculation,
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


def my_import(request):
    zf = zipfile.ZipFile("/Users/Kai/Downloads/AAA.zip")
    data = json.loads(zf.open("data.json").read())
    for product in data:
        # No implemented yet
        # new_product.creation_date = product["creation_date"]
        # new_product.static_block = product["static_block"]
        # new_product.price_calculator = product["price_calculation"]
        # new_product.template = product[""]
        # new_product.supplier = product["supplier"]
        new_product, created = Product.objects.get_or_create(uid=product["uid"])
        new_product.name = product["name"]
        new_product.sku = product["sku"]
        new_product.slug = product["slug"]
        new_product.price = product["price"]
        new_product.effective_price = product["effective_price"]
        new_product.price_unit = product["price_unit"]
        new_product.unit = product["unit"]
        new_product.short_description = product["short_description"]
        new_product.description = product["description"]
        new_product.meta_title = product["meta_title"]
        new_product.meta_keywords = product["meta_description"]
        new_product.meta_description = product["meta_description"]
        new_product.for_sale = product["for_sale"]
        new_product.for_sale_price = product["for_sale_price"]
        new_product.active = product["active"]
        new_product.deliverable = product["deliverable"]
        new_product.manual_delivery_time = product["manual_delivery_time"]
        new_product.delivery_time = product["delivery_time"]
        new_product.order_time = product["order_time"]
        new_product.manage_stock_amount = product["manage_stock_amount"]
        new_product.stock_amount = product["stock_amount"]
        new_product.active_packing_unit = product["active_packing_unit"]
        new_product.packing_unit = product["packing_unit"]
        new_product.packing_unit_unit = product["packing_unit_unit"]
        new_product.price_calculation = product["price_calculation"]
        new_product.weight = product["weight"]
        new_product.height = product["height"]
        new_product.length = product["length"]
        new_product.width = product["width"]
        new_product.variants_display_type = product["variants_display_type"]
        new_product.variant_position = product["variant_position"]
        new_product.active_name = product["active_name"]
        new_product.active_sku = product["active_sku"]
        new_product.active_short_description = product["active_short_description"]
        new_product.active_static_block = product["active_static_block"]
        new_product.active_description = product["active_description"]
        new_product.active_price = product["active_price"]
        new_product.active_for_sale = product["active_for_sale"]
        new_product.active_for_sale_price = product["active_for_sale_price"]
        new_product.active_images = product["active_images"]
        new_product.active_related_products = product["active_related_products"]
        new_product.active_accessories = product["active_accessories"]
        new_product.active_meta_title = product["active_meta_title"]
        new_product.active_meta_description = product["active_meta_description"]
        new_product.active_meta_keywords = product["active_meta_keywords"]
        new_product.active_dimensions = product["active_dimensions"]
        new_product.active_price_calculation = product["active_price_calculation"]
        new_product.active_base_price = product["active_base_price"]
        new_product.base_price_unit = product["base_price_unit"]
        new_product.base_price_amount = product["base_price_amount"]
        new_product.sku_manufacturer = product["sku_manufacturer"]
        new_product.type_of_quantity_field = product["type_of_quantity_field"]

        # Ordered at
        if product["ordered_at"]:
            new_product.ordered_at = product["ordered_at"]

        # Manufacturer
        manufacturer, created = Manufacturer.objects.get_or_create(name=product["manufacturer"])
        new_product.manufacturer = manufacturer

        # Tax
        try:
            tax, created = Tax.objects.get_or_create(rate=product["tax"])
            new_product.tax = tax
        except ValueError:
            pass

        new_product.save()

        # Images
        new_product.images.all().delete()
        for image in product.get("images"):
            new_image = Image(
                title=image["title"],
                position=image["position"],
                content=new_product,
            )
            new_image.image.save(
                image["name"],
                ContentFile(zf.open(image["path"]).read())
            )
            new_image.save()

        # Attachments
        new_product.attachments.all().delete()
        for attachment in product.get("attachments"):
            new_attachment = ProductAttachment(
                title=attachment["title"],
                description=attachment["description"],
                position=attachment["position"],
                product=new_product,
            )
            new_attachment.file.save(
                attachment["name"],
                ContentFile(zf.open(attachment["path"]).read())
            )
            new_attachment.save()

        # Local properties
        for ppr in ProductsPropertiesRelation.objects.filter(product=new_product, property__local=True):
            ppr.property.options.all().delete()
            ppr.property.delete()
            ppr.delete()

        for prop in product["local_properties"]:
            new_prop = Property.objects.create(
                uid=prop["uid"],
                name=prop["name"],
                type=prop["type"],
                local=True,
            )
            for option in prop["options"]:
                PropertyOption.objects.create(
                    property=new_prop,
                    uid=option["uid"],
                    name=option["name"],
                    price=option["price"],
                    position=option["position"],
                )
            ProductsPropertiesRelation.objects.create(
                product=new_product,
                property=new_prop,
                position=prop["position"])

        # Property groups and global properties
        for property_group in product["property_groups"]:
            new_pg, created = PropertyGroup.objects.get_or_create(uid=property_group["uid"])
            new_pg.name = property_group["name"]
            new_pg.position = property_group["position"]
            new_pg.save()

            for prop in property_group["properties"]:
                new_prop, created = Property.objects.get_or_create(uid=prop["uid"])
                new_prop.name = prop["name"]
                new_prop.title = prop["title"]
                new_prop.position = prop["position"]
                new_prop.unit = prop["unit"]
                new_prop.display_on_product = prop["display_on_product"]
                new_prop.local = prop["local"]
                new_prop.variants = prop["variants"]
                new_prop.filterable = prop["filterable"]
                new_prop.configurable = prop["configurable"]
                new_prop.type = prop["type"]
                new_prop.price = prop["price"]
                new_prop.display_price = prop["display_price"]
                new_prop.add_price = prop["add_price"]
                new_prop.unit_min = prop["unit_min"]
                new_prop.unit_max = prop["unit_max"]
                new_prop.unit_step = prop["unit_step"]
                new_prop.decimal_places = prop["decimal_places"]
                new_prop.required = prop["required"]
                new_prop.step_type = prop["step_type"]
                new_prop.step = prop["step"]
                new_prop.save()

                gpr, created = GroupsPropertiesRelation.objects.get_or_create(
                    group=new_pg,
                    property=new_prop,
                )

                gpr.position = prop["group_position"]
                gpr.save()

                # Options
                for option in prop["options"]:
                    po, created = PropertyOption.objects.get_or_create(
                        uid=option["uid"],
                        property=new_prop
                    )
                    po.name = option["name"]
                    po.price = option["price"]
                    po.position = option["position"]
                    po.save()

                # Steps
                FilterStep.objects.filter(property=new_prop).delete()
                for step in prop["steps"]:
                    FilterStep.objects.create(
                        property=new_prop,
                        start=step["start"],
                    )

                new_pg.products.add(new_product)

    # Second run for dependencies to other products
    for product in data:
        new_product = Product.objects.get(uid=product["uid"])

        # Accessories
        ProductAccessories.objects.filter(product=new_product).delete()
        for accessory in product["accessories"]:
            try:
                new_accessory = Product.objects.get(uid=accessory["uid"])
            except Product.DoesNotExist:
                pass
            else:
                ProductAccessories.objects.create(
                    product=new_product,
                    accessory=new_accessory,
                    position=accessory["position"],
                    quantity=accessory["quantity"]
                )

        # Related products
        new_product.related_products.all().delete()
        for related_product_uid in product["related_products"]:
            try:
                related_product = Product.objects.get(uid=related_product_uid)
            except Product.DoesNotExist:
                pass
            else:
                new_product.related_products.add(related_product)

        # Parent
        if product["parent"]:
            try:
                parent = Product.objects.get(uid=product["parent"])
            except Product.DoesNotExist:
                pass
            else:
                new_product.parent = parent

        # Default variant
        try:
            default_variant = Product.objects.get(uid=product["default_variant"])
        except Product.DoesNotExist:
            pass
        else:
            new_product.default_variant = default_variant

        # Category variant
        try:
            new_product.category_variant = Product.objects.get(uid=product["category_variant"])
        except Product.DoesNotExist:
            new_product.category_variant = product["category_variant"]

        # Property values
        ProductPropertyValue.objects.filter(product=new_product).delete()
        for property_value in product["property_values"]:
            try:
                parent = Product.objects.get(uid=property_value["parent"])
            except Product.DoesNotExist:
                logger.info("Parent for property value not found: {} {}".format(new_product.uid, property_value["parent"]))
                continue

            try:
                prop = Property.objects.get(uid=property_value["property"])
            except Property.DoesNotExist:
                logger.info("Property for property value not found: {} {}".format(new_product.uid, property_value["property"]))
                continue

            if prop.local or (property_value["type"] == PROPERTY_SELECT_FIELD):
                try:
                    value = PropertyOption.objects.get(uid=property_value["value"]).pk
                except PropertyOption.DoesNotExist:
                    logger.info("PropertyOption for property value not found: {} {}".format(new_product.uid, property_value["value"]))
                    continue
            else:
                value = property_value["value"]

            ppg = PropertyGroup.objects.get(uid=property_value["property_group"])
            ProductPropertyValue.objects.create(
                product=new_product,
                parent_id=parent.id,
                property=prop,
                property_group=ppg,
                value=value,
                type=property_value["type"],
            )

        new_product.sub_type = product["sub_type"]
        new_product.save()

    return HttpResponse("Finished!")
