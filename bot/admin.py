from django.contrib import admin
from .models import UserProfile
from .models import Categories
from .models import Products
from .models import ProductVariations
from .models import ImageForMain
from .models import BackendHall
from .models import OrderBackendHall
from .models import Basket
from .models import AboutUs
from .models import Contacts


@admin.register(ProductVariations)
class ProductVariationsAdmin(admin.ModelAdmin):
    search_fields = ['product__name', 'size', 'title']
    list_display = ['product', 'size', 'price', 'title']

admin.site.register(UserProfile)
admin.site.register(Categories)
admin.site.register(Products)
admin.site.register(ImageForMain)
admin.site.register(BackendHall)
admin.site.register(OrderBackendHall)
admin.site.register(Basket)
admin.site.register(AboutUs)
admin.site.register(Contacts)
