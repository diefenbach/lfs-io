# Python imports
import json
import uuid
import zipfile

# django imports
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.template.defaultfilters import slugify

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
from lfs.manufacturer.models import Manufacturer

# lfs_io imports
from lfs_io.forms import ImportForm

# django imports
from django.core.files.base import ContentFile

# Load logger
import logging
logger = logging.getLogger("default")


@permission_required("core.manage_shop")
def import_view(request, template_name="lfs_io/import.html"):
    form = ImportForm()
    if request.method == "POST":
        _import(request)
        return HttpResponse("Finished!")
    else:
        return render_to_response(template_name, RequestContext(request, {
            "form": form,
        }))


def _import(request):
    zf = zipfile.ZipFile(request.FILES.get("my_file"))
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
        # new_product.delivery_time = product["delivery_time"]
        new_product.order_time = product["order_time"]
        new_product.manage_stock_amount = product["manage_stock_amount"]
        new_product.stock_amount = product["stock_amount"]
        new_product.active_packing_unit = product["active_packing_unit"]
        new_product.packing_unit = product["packing_unit"]
        new_product.packing_unit_unit = product["packing_unit_unit"] or ""
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
        new_product.base_price_unit = product["base_price_unit"] or ""
        new_product.base_price_amount = product["base_price_amount"]
        new_product.sku_manufacturer = product["sku_manufacturer"]
        new_product.type_of_quantity_field = product["type_of_quantity_field"]

        # Ordered at
        if product["ordered_at"]:
            new_product.ordered_at = product["ordered_at"]

        # Manufacturer
        manufacturer, created = Manufacturer.objects.get_or_create(
            name=product["manufacturer"],
            slug=slugify(product["manufacturer"]),
        )
        new_product.manufacturer = manufacturer

        # Tax
        try:
            tax, created = Tax.objects.get_or_create(rate=product["tax"])
            new_product.tax = tax
        except ValueError:
            pass

        new_product.save()
        if created:
            logger.info("Product created {}".format(product["uid"]))
        else:
            logger.info("Product updated {}".format(product["uid"]))

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
                type=prop.get("type", 0),
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
                new_prop.configurable = prop["configurable"] or False
                new_prop.type = prop["type"]
                new_prop.price = prop["price"]
                new_prop.display_price = prop["display_price"] or False
                new_prop.add_price = prop["add_price"] or False
                new_prop.unit_min = prop["unit_min"]
                new_prop.unit_max = prop["unit_max"]
                new_prop.unit_step = prop["unit_step"]
                new_prop.decimal_places = prop["decimal_places"] or 0
                new_prop.required = prop["required"] or False
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
                    try:
                        po = PropertyOption.objects.get(uid=option["uid"])
                    except PropertyOption.DoesNotExist:
                        po = PropertyOption.objects.create(
                            uid=option["uid"],
                            property=new_prop,
                        )
                    po.property = new_prop
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
                logger.info("Parent {} not found for product {}".format(product["parent"], new_product.uid))
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

            if prop.local:
                ProductPropertyValue.objects.create(
                    product=new_product,
                    parent_id=parent.id,
                    property=prop,
                    value=value,
                    type=property_value["type"],
                    property_group=None,
                )
            else:
                # Save the values for every group of the property. In 0.8 there
                # was only one value for a property for all groups
                for group in prop.groups.all():
                    ProductPropertyValue.objects.create(
                        product=new_product,
                        parent_id=parent.id,
                        property=prop,
                        value=value,
                        type=property_value["type"],
                        property_group=group,
                    )

        new_product.sub_type = product["sub_type"]
        new_product.save()
