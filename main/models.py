from django.utils.deconstruct import deconstructible
from django.contrib.auth.models import AbstractUser, User
from django.db import models
from django.utils.translation import gettext_lazy as _
from .managers import CustomUserManager
from django.utils import timezone
import random
from etlo.settings import ROOT
from PIL import Image
from io import BytesIO
from django.core.files import File
from django_softdelete.models import SoftDeleteModel
from django.core.validators import MaxValueValidator, MinValueValidator
import os


def rand():
    while True:
        code = random.randint(1111111111, 9999999999)
        return code


@deconstructible
class PathRename(object):

    def __init__(self, sub_path, part):
        self.path = sub_path
        self.part = part

    def __call__(self, instance, filename):
        ext = filename.split('.')[-1]
        filename = '{}.{}'.format(
            self.part + '-' + timezone.now().strftime("%m/%d/%Y-%H:%M:%S"), ext)
        return os.path.join(self.path, filename)


class Country(models.Model):
    name = models.CharField(max_length=50, null=True, unique=True)
    symbol = models.CharField(max_length=3, null=True)
    dial_code = models.CharField(max_length=5, null=True)
    image = models.CharField(max_length=200, null=True)
    have_service = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = ' Countries '

    def get_flag(self):
        if not self.image:
            return ''
        return self.image

    def __str__(self):
        return self.symbol


class State(models.Model):
    country = models.ForeignKey(
        Country, related_name='states', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10)
    city = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = ' States '

    def __str__(self):
        return self.name


class City(models.Model):
    state = models.ForeignKey(
        State, related_name='cities', on_delete=models.CASCADE)
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name_plural = ' Cities '

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    password = models.CharField(
        _("password"), max_length=128, null=True, default=None, blank=True)
    username_validator = None
    username = None
    country_code = models.ForeignKey(
        Country, related_name='users', on_delete=models.CASCADE, null=True, blank=True)
    phone_number = models.CharField(
        max_length=12, unique=True, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    first_name = models.CharField(max_length=50, null=True, blank=True)
    profile_image = models.ImageField(upload_to=PathRename(
        'users-pic', 'users-pic'), null=True, blank=True)
    id_image = models.ImageField(upload_to=PathRename(
        'users-pic', 'users-pic'), null=True, blank=True)
    last_name = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    etlo_id = models.CharField(
        max_length=10, default=rand, editable=False, unique=True)
    email_verification = models.BooleanField(default=False, null=True)
    phone_verification = models.BooleanField(default=False, null=True)
    image_verification = models.BooleanField(default=False, null=True)
    id_verification = models.BooleanField(default=False, null=True)
    image_verification_error = models.CharField(
        max_length=150, null=True, blank=True)
    id_verification_error = models.CharField(
        max_length=150, null=True, blank=True)

    def get_profile_image(self):
        if not self.profile_image:
            return ''
        return ROOT + self.profile_image.url

    def get_id_image(self):
        if not self.id_image:
            return ''
        return ROOT + self.id_image.url

    def is_verified(self):
        if self.email_verification and self.phone_verification and self.id_verification and self.image_verification:
            return True
        else:
            return ''

    USERNAME_FIELD = 'etlo_id'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.etlo_id


class Address(SoftDeleteModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=30)
    reciever_first_name = models.CharField(max_length=30)
    reciever_last_name = models.CharField(max_length=30)
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    state = models.ForeignKey(State, on_delete=models.CASCADE)
    address = models.CharField(max_length=300)
    postal_code = models.CharField(max_length=15)
    phone = models.CharField(max_length=10)


class Currency(SoftDeleteModel):
    last_modify_user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, null=True)
    add_date = models.DateTimeField(auto_now_add=True, editable=True)
    last_modify_date = models.DateTimeField(auto_now=True, editable=True)
    name = models.CharField(max_length=30, null=True)
    symbol = models.CharField(max_length=3, null=True)
    country = models.ForeignKey(
        Country, related_name='currency', on_delete=models.CASCADE)
    icon = models.CharField(max_length=30)
    is_active = models.BooleanField(default=True)
    to_irt = models.FloatField(null=True)

    class Meta:
        verbose_name_plural = ' Currencies '
        constraints = [
            models.UniqueConstraint(
                fields=["symbol", "country"],
                name='CurrencyUniqueConstraint'
            )
        ]

    def get_flag(self):
        if not self.country.image:
            return ''
        return self.country.image

    def __str__(self):
        return self.symbol


class Wallet(SoftDeleteModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    balance = models.FloatField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "currency"],
                name='WalletUniqueConstraint'
            )
        ]

    def get_currency_name(self):
        return self.currency.icon

    def get_flag(self):
        return self.currency.get_flag()

    def get_icon(self):
        return self.currency.icon

    def get_symbol(self):
        return self.currency.icon


class Transaction(SoftDeleteModel):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    type = models.IntegerField(validators=[MinValueValidator(1)])
    amount = models.FloatField()
    details = models.CharField(max_length=150)
    bank_code = models.CharField(max_length=30, null=True)

    def get_currency_name(self):
        return self.wallet.currency.icon

    def get_flag(self):
        return self.wallet.currency.get_flag()

    def get_icon(self):
        return self.wallet.currency.icon

    def get_symbol(self):
        return self.currency.icon


class MobileConfirmationCode(models.Model):
    country_code = models.CharField(max_length=3, null=True, blank=True)
    phone_number = models.CharField(max_length=10)
    code = models.IntegerField(validators=[MinValueValidator(1)], )
    date = models.DateTimeField(auto_now=True, editable=True)


class EmailConfirmationCode(models.Model):
    email = models.EmailField()
    code = models.IntegerField(validators=[MinValueValidator(1)], )
    date = models.DateTimeField(auto_now=True, editable=True)


class Notification(models.Model):
    user = models.ForeignKey(
        CustomUser, related_name='notification', on_delete=models.CASCADE)
    title = models.CharField(max_length=50)
    text = models.CharField(max_length=300)
    icon = models.CharField(max_length=30)
    read = models.BooleanField(default=False)
    date = models.DateTimeField(auto_now=True, editable=True)


class Department(SoftDeleteModel):
    last_modify_user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, null=True)
    add_date = models.DateTimeField(auto_now_add=True, editable=True)
    last_modify_date = models.DateTimeField(auto_now=True, editable=True)
    name = models.CharField(max_length=50)
    details = models.CharField(max_length=200)
    icon = models.CharField(max_length=30)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = ' Department '
        verbose_name_plural = ' Departments '


class DepartmentService(SoftDeleteModel):
    last_modify_user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, null=True)
    add_date = models.DateTimeField(auto_now_add=True, editable=True)
    last_modify_date = models.DateTimeField(auto_now=True, editable=True)
    department = models.ForeignKey(
        Department, related_name='services', on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
    details = models.CharField(max_length=200)
    icon = models.CharField(max_length=30)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = ' Department Service '
        verbose_name_plural = ' Department Services '


class DepartmentBanner(SoftDeleteModel):
    last_modify_user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, null=True)
    add_date = models.DateTimeField(auto_now_add=True, editable=True)
    last_modify_date = models.DateTimeField(auto_now=True, editable=True)
    name = models.CharField(max_length=50)
    department = models.ForeignKey(
        Department, related_name='banners', on_delete=models.CASCADE)
    img = models.ImageField(upload_to=PathRename(
        'company-banners', 'company-banners'), null=True, blank=True)
    large = models.ImageField(upload_to=PathRename(
        'company-banners-large', 'company-banners-large'), null=True, blank=True)
    medium = models.ImageField(upload_to=PathRename(
        'company-banners-medium', 'company-banners-medium'), null=True, blank=True)
    small = models.ImageField(upload_to=PathRename(
        'company-banners-small', 'company-banners-small'), null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Departments Banner'
        verbose_name_plural = 'Departments Banners'

    def get_image(self):
        if not self.img:
            return ''
        return ROOT + self.img.url

    def get_small_image(self):
        if not self.small:
            if not self.img:
                return ''
            else:
                self.small = self.resize(self.img, (320, 100))
                self.save()
                return ROOT + self.small.url

        else:
            return ROOT + self.small.url

    def get_medium_image(self):
        if not self.medium:
            if not self.img:
                return ''
            else:
                self.medium = self.resize(self.img, (645, 200))
                self.save()
                return ROOT + self.medium.url

        else:
            return ROOT + self.medium.url

    def get_large_image(self):
        if not self.large:
            if not self.img:
                return ''
            else:
                self.large = self.resize(self.img, (1290, 400))
                self.save()
                return ROOT + self.large.url

        else:
            return ROOT + self.large.url

    def resize(self, image, size):
        img = Image.open(image)
        img.convert('RGB')
        img.thumbnail(size)

        thumb_io = BytesIO()
        img.save(thumb_io, 'JPEG', quality=300)

        thumbnail = File(thumb_io, name=image.name)

        return thumbnail


class Banner(SoftDeleteModel):
    last_modify_user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, null=True)
    add_date = models.DateTimeField(auto_now_add=True, editable=True)
    last_modify_date = models.DateTimeField(auto_now=True, editable=True)
    name = models.CharField(max_length=50)
    img = models.ImageField(upload_to=PathRename(
        'company-banners', 'company-banners'), null=True, blank=True)
    large = models.ImageField(upload_to=PathRename(
        'company-banners-large', 'company-banners-large'), null=True, blank=True)
    medium = models.ImageField(upload_to=PathRename(
        'company-banners-medium', 'company-banners-medium'), null=True, blank=True)
    small = models.ImageField(upload_to=PathRename(
        'company-banners-small', 'company-banners-small'), null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Departments Banner'
        verbose_name_plural = 'Departments Banners'

    def get_image(self):
        if not self.img:
            return ''
        return ROOT + self.img.url

    def get_small_image(self):
        if not self.small:
            if not self.img:
                return ''
            else:
                self.small = self.resize(self.img, (320, 100))
                self.save()
                return ROOT + self.small.url

        else:
            return ROOT + self.small.url

    def get_medium_image(self):
        if not self.medium:
            if not self.img:
                return ''
            else:
                self.medium = self.resize(self.img, (645, 200))
                self.save()
                return ROOT + self.medium.url

        else:
            return ROOT + self.medium.url

    def get_large_image(self):
        if not self.large:
            if not self.img:
                return ''
            else:
                self.large = self.resize(self.img, (1290, 400))
                self.save()
                return ROOT + self.large.url

        else:
            return ROOT + self.large.url

    def resize(self, image, size):
        img = Image.open(image)
        img.convert('RGB')
        img.thumbnail(size)

        thumb_io = BytesIO()
        img.save(thumb_io, 'JPEG', quality=300)

        thumbnail = File(thumb_io, name=image.name)

        return thumbnail


class Chat(models.Model):
    date = models.DateTimeField(auto_now_add=True)
    owner = models.ForeignKey(
        CustomUser, related_name='chats', on_delete=models.CASCADE)
    user = models.ForeignKey(
        CustomUser, related_name='joined_chats', on_delete=models.CASCADE)
    text = models.CharField(max_length=250)
    image = models.ImageField(PathRename('chats', 'chats'), null=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    service = models.ForeignKey(
        DepartmentService, on_delete=models.CASCADE, null=True, blank=True)
    admin_read = models.BooleanField(default=False)
    user_read = models.BooleanField(default=False)
    is_order = models.BooleanField(default=False)
    order_id = models.IntegerField(null=True, blank=True)

    def get_image(self):
        if not self.image:
            return ''
        return ROOT + self.image.url


class BankCard(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    number = models.CharField(max_length=16)
    full_name = models.CharField(max_length=100)
    bank_name = models.CharField(max_length=100)
    status = models.IntegerField(default=0)
    image = models.ImageField(upload_to=PathRename('bankcard', 'bankcard'))
    date = models.DateTimeField(auto_now_add=True)


class BankSheba(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    number = models.CharField(max_length=16)
    full_name = models.CharField(max_length=100)
    bank_name = models.CharField(max_length=100)
    status = models.IntegerField(default=0)
    date = models.DateTimeField(auto_now_add=True)


class Withdraw(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    currency = models.ForeignKey(Currency, on_delete=models.CASCADE)
    banksheba = models.ForeignKey(
        BankSheba, on_delete=models.CASCADE, null=True)
    bankcard = models.ForeignKey(BankCard, on_delete=models.CASCADE, null=True)
    amount = models.FloatField()
    status = models.IntegerField(default=0)
    date = models.DateTimeField(auto_now_add=True)
