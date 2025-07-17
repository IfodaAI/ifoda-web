import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils.timezone import now


class Language(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


class TelegramUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    telegram_id = models.BigIntegerField(unique=True)
    fullname = models.CharField(max_length=255)
    username = models.CharField(max_length=255, null=True, blank=True)
    phone_number = models.CharField(max_length=20)
    language = models.ForeignKey(Language, on_delete=models.SET_NULL, null=True, blank=True)
    region=models.CharField(max_length=100,blank=True,null=True)
    district=models.CharField(max_length=100,blank=True,null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.fullname}.{self.phone_number} ({self.telegram_id})"


class CustomUserManager(BaseUserManager):

    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("The phone number is required")

        extra_fields.setdefault('is_active', True)
        user = self.model(phone_number=phone_number, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(phone_number, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fullname = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15, unique=True)  # Unique field
    image = models.ForeignKey('Image', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)  # Required field
    is_staff = models.BooleanField(default=False)  # Required field for Django admin compatibility

    objects = CustomUserManager()

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['fullname']

    def __str__(self):
        return self.phone_number


class Branch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    branch_id = models.CharField(max_length=255, null=True, blank=True, default='1')
    telegram_id = models.BigIntegerField(unique=True,null=True, blank=True)
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=15)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Order(models.Model):
    STATUS_CHOICE = (
        ('PENDING', 'pending'),
        ('PROCESS', 'process'),
        ('COMPLETED', 'completed'),
        ('IN_PAYMENT', 'in_payment'),
    )
    DELIVERY_CHOICE = (
        ('DELIVERY', 'delivery'),
        ('PICKUP', 'pick_up'),
    )
    PAYMENT_CHOICE = (
        ('PAYME', 'payMe'),
        ('CLICK', 'click'),
        ('CASH', 'cash'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    order_date = models.DateTimeField(auto_now_add=True)
    order_updated_date = models.DateTimeField(auto_now=True)
    total_amount = models.DecimalField(max_digits=20, decimal_places=2, default=0.00)
    status = models.CharField(max_length=50, choices=STATUS_CHOICE, default='PENDING')
    delivery_method = models.CharField(max_length=50, choices=DELIVERY_CHOICE, default='DELIVERY')
    payment_method = models.CharField(max_length=50, choices=PAYMENT_CHOICE, default='CASH')
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, null=True, blank=True)
    delivery_latitude = models.DecimalField(max_digits=9, decimal_places=6, default=0.00)
    delivery_longitude = models.DecimalField(max_digits=9, decimal_places=6, default=0.00)
    delivery_price = models.DecimalField(max_digits=20, decimal_places=2, default=0.00, null=True, blank=True)


class Messages(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='messages')
    type = models.CharField(max_length=50, choices=[('TEXT', 'text'), ('IMAGE', 'image')], default='TEXT')
    sender = models.CharField(max_length=50, choices=[('USER', 'User'), ('BOT', 'Bot')])
    status = models.CharField(max_length=50, choices=[('READ', 'read'), ('UNREAD', 'unread')], default='UNREAD')
    text = models.TextField(null=True, blank=True)
    image_url = models.URLField(null=True, blank=True)
    image = models.ImageField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.sender} ({self.timestamp}): {self.text}'

class Image(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    url = models.URLField()
    order = models.ForeignKey(Order, related_name="images", on_delete=models.CASCADE, null=True, blank=True)
    image = models.ImageField(null=True, blank=True)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Pills(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_id = models.CharField(max_length=255, null=True, blank=True, default='1')
    name = models.CharField(max_length=255)
    description = models.TextField()
    price = models.IntegerField()
    spic = models.CharField(max_length=17, null=True, blank=True, default='03808001001000000')
    package_code = models.CharField(max_length=20, null=True, blank=True, default='1476512')
    image = models.ImageField(null=True, blank=True)
    small_product=models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class Diseases(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    pills = models.ManyToManyField(Pills, related_name='diseases')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=True)


class OrderToPills(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_pills')
    pills = models.ForeignKey(Pills, on_delete=models.CASCADE)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class OrderToDiseases(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_diseases')
    diseases = models.ForeignKey(Diseases, on_delete=models.CASCADE)
    status = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class OrderItems(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    pills = models.ForeignKey(Pills, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    logix_status = models.CharField(max_length=50, choices=[('SUCCESS', 'success'), ('ERROR', 'error')], default='SUCCESS', null=True, blank=True)


class Payment(models.Model):
    STATUS_CHOICE = (
        ('Pending', 'pending'),
        ('Completed', 'completed'),
        ('Failed', 'failed'),
    )
    PAYMENT_CHOICE = (
        ('PAYME', 'payMe'),
        ('CLICK', 'click'),
        ('CASH', 'cash'),
    )
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, unique=True)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_CHOICE, default='CASH')
    payment_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_status = models.CharField(max_length=50, choices=STATUS_CHOICE, null=True)


class DeliveryCost(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    price = models.BigIntegerField(default=1000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(default=now())

    def save(self, *args, **kwargs):
        if self.id:
            self.updated_at = now()
        super().save(*args, **kwargs)


class PaymeTransaction(models.Model):
    _id = models.CharField(max_length=255, null=True, blank=False)
    transaction_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_id = models.CharField(max_length=255, null=True, blank=True)
    amount = models.FloatField(null=True, blank=True)
    time = models.BigIntegerField(null=True, blank=True)
    perform_time = models.BigIntegerField(null=True, default=0)
    cancel_time = models.BigIntegerField(null=True, default=0)
    state = models.IntegerField(null=True, default=1)
    reason = models.CharField(max_length=255, null=True, blank=True)
    created_at_ms = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return str(self._id)
