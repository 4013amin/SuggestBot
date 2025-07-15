from django.shortcuts import render, get_object_or_404
from . import models


# Create your views here.

def index(request, product_id):
    product = get_object_or_404(
        models.Product,
        id=product_id
    )

    recommended = models.Product.objects.filter(category=product.category).exclude(id=product.id)[:5]

    data = {
        'product': product,
        'recommended': recommended
    }
    return render(request, 'index.html', data)
