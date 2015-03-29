import json
import zipfile
import StringIO

# django imports
from django.http import HttpResponse

# lfs imports
from lfs.export.utils import register


def export(request, export):
    """Generic export method.
    """
    result = []
    for product in export.get_products():

        string = StringIO.StringIO()
        archive = zipfile.ZipFile(string, "w")

        images = []
        for image in product.images.all():
            images.append(image.image.name)
            archive.write(image.image.file.name, image.image.name)

        related_products = []
        for related_product in product.related_products.all():
            related_products.append(related_product.uid)

        accessories = []
        for accessory in product.accessories.all():
            accessories.append(accessory.uid)

        result.append({
            "uid": product.uid,
            "name": product.name,
            "slug": product.slug,
            "price": product.price,
            "price_calculator": product.price_calculator,
            "effective_price": product.effective_price,
            "price_unit": product.price_unit,
            "unit": product.unit,
            "short_description": product.short_description,
            "description": product.description,
            "images": images,
            "meta_title": product.meta_title,
            "meta_keywords": product.meta_keywords,
            "meta_description": product.meta_description,
            "related_products": related_products,
            "accessories": accessories,
        })

    archive.writestr("data.json", json.dumps(result))
    response = HttpResponse(string.getvalue(), content_type="application/zip")
    response["Content-Disposition"] = "attachment; filename=%s.zip" % export.name

    return response

register(export, "io")
