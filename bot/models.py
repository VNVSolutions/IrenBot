from django.db import models
from django.forms import ImageField
from django.urls import reverse


class ImageForMain(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='image', blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = "backend_imageformain"


class Categories(models.Model):
    categories_name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True, verbose_name="URL")
    smile = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.categories_name

    class Meta:
        db_table = "backend_categories"


class Products(models.Model):
    image_products = models.ImageField(upload_to='img_products', blank=True)
    name = models.CharField(max_length=255)
    smile = models.CharField(max_length=255, blank=True, null=True)
    articul = models.CharField(max_length=255, null=True, blank=True)
    ingredients = models.TextField(blank=True, null=True)
    is_have_variations = models.BooleanField()
    price = models.IntegerField(null=True)
    categories = models.ForeignKey("Categories", on_delete=models.CASCADE)

    def get_first_variation(self):
        return ProductVariations.objects.filter(product_id=self.id).first()

    def get_variations(self):
        return ProductVariations.objects.filter(product_id=self.id)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('categories', kwargs={'cat_id': self.pk})

    class Meta:
        db_table = "backend_products"


class ProductVariations(models.Model):
    product = models.ForeignKey("Products", on_delete=models.PROTECT)
    size = models.CharField(max_length=255)
    price = models.IntegerField()
    title = models.CharField(max_length=255, null=True)

    def __str__(self):
        return f"{self.product} - {self.size}"

    class Meta:
        db_table = "backend_productvariations"


class UserProfile(models.Model):
    telegram_id = models.BigIntegerField(null=True)
    username = models.CharField(max_length=256, null=True)
    name = models.CharField(max_length=255, null=True)

    def __str__(self):
        return f"{self.username}, {self.telegram_id}"

    class Meta:
        db_table = "userprofile"


class BackendHall(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    size = models.CharField(max_length=255)
    img = models.ImageField(upload_to='img_products/', blank=True)

    def __str__(self):
        return f"{self.name}"

    class Meta:
        managed = False
        db_table = 'backend_hall'


class OrderBackendHall(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    hall = models.ForeignKey(BackendHall, on_delete=models.CASCADE)
    contact = models.CharField(max_length=256, verbose_name="Контакти", null=True)

    def __str__(self):
        return f"{self.user}, {self.hall}"

    class Meta:
        managed = False
        db_table = 'backend_order_hall'


class Basket(models.Model):
    user = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    products = models.ForeignKey(Products, on_delete=models.CASCADE)
    amount = models.IntegerField(null=True)

    def __str__(self):
        return f"{self.user}"

    class Meta:
        managed = False
        db_table = 'backend_basket'


class AboutUs(models.Model):
    image_products = models.ImageField(upload_to='img_products', blank=True)
    text = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.text}"

    class Meta:
        db_table = "backend_about_us"


class Contacts(models.Model):
    text = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.text}"

    class Meta:
        db_table = "backend_contacts"
