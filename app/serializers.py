from rest_framework import serializers
from .models import Pills, Branch, Diseases, Order, OrderToPills, OrderToDiseases, User, Image, OrderItems, Payment, \
    TelegramUser, Language, DeliveryCost, Messages
from django.contrib.auth import authenticate


class PaymeLinkSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)


class ClickPrepareRequestSerializer(serializers.Serializer):
    click_trans_id = serializers.IntegerField(help_text="Transaction ID in CLICK system")
    service_id = serializers.IntegerField(help_text="ID of the service")
    click_paydoc_id = serializers.IntegerField(help_text="Payment ID in CLICK system")
    merchant_trans_id = serializers.CharField(max_length=255, help_text="Order ID or account ID")
    amount = serializers.FloatField(help_text="Payment amount in soums")
    action = serializers.IntegerField(help_text="Action type: 0 for Prepare, 1 for Complete")
    sign_time = serializers.CharField(help_text="Payment date in format 'YYYY-MM-DD HH:mm:ss'")
    sign_string = serializers.CharField(help_text="MD5 hash for request validation")


class ClickCompleteRequestSerializer(serializers.Serializer):
    click_trans_id = serializers.IntegerField(help_text="Transaction ID in CLICK system")
    service_id = serializers.IntegerField(help_text="ID of the service")
    click_paydoc_id = serializers.IntegerField(help_text="Payment ID in CLICK system")
    merchant_trans_id = serializers.CharField(max_length=255, help_text="Order ID or account ID")
    amount = serializers.FloatField(help_text="Payment amount in soums")
    action = serializers.IntegerField(help_text="Action type: 0 for Prepare, 1 for Complete")
    sign_time = serializers.CharField(help_text="Payment date in format 'YYYY-MM-DD HH:mm:ss'")
    sign_string = serializers.CharField(help_text="MD5 hash for request validation")


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Messages
        fields = '__all__'
        read_only_fields = ['id', 'timestamp']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.image:
            request = self.context.get('request')
            if request:
                data['image_url'] = request.build_absolute_uri(instance.image.url)
            else:
                data['image_url'] = instance.image.url
        return data


class TelegramUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramUser
        fields = '__all__'


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = '__all__'


class OrderItemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItems
        fields = "__all__"
    
    def to_representation(self, instance):
        data = super().to_representation(instance)

        data["pills"] = instance.pills.name
        return data

class PillsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pills
        fields = '__all__'


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = '__all__'


class DiseasesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Diseases
        fields = '__all__'


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image
        fields = '__all__'


# class OrderSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Order
#         fields = '__all__'
class OrderSerializer(serializers.ModelSerializer):
    orderitems_set = OrderItemsSerializer(many=True, read_only=True)
    class Meta:
        model = Order
        fields = "__all__"

    def to_representation(self, instance):
        data = super().to_representation(instance)

        data["user"] = instance.user.fullname
        data["phone_number"] = instance.user.phone_number
        data["region"] = instance.user.region
        data["district"] = instance.user.district
        data["branch"] = instance.branch.name if instance.branch else None
        data["is_paid"] = Payment.objects.filter(order=instance).exists()
        return data

class OrderToPillsSerializer(serializers.ModelSerializer):
    pills=PillsSerializer()
    class Meta:
        model = OrderToPills
        fields = '__all__'


class OrderToDiseasesSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderToDiseases
        fields = '__all__'


class DeliveryCostSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryCost
        fields = '__all__'


# Register your models here.
class UserSignupSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['fullname', 'phone_number']

    def create(self, validated_data):
        if User.objects.filter(phone_number=validated_data['phone_number']).exists():
            raise serializers.ValidationError("User with this phone number already exists!")
        user = User.objects.create_user(
            phone_number=validated_data['phone_number'],
            fullname=validated_data.get('fullname', ''),
        )
        user.save()
        return user

class UserSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
    )

    class Meta:
        model = User
        fields = (
            "id",
            "fullname",
            "phone_number",
            "created_at",
            "is_superuser",
            "is_staff",
            "password",
        )

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class UserLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        user = authenticate(phone_number=data['phone_number'], password=data['password'])
        if not user:
            raise serializers.ValidationError("Invalid phone number or password!")
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled!")
        data['user'] = user
        return data


# user me serializers
class UserMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'fullname', 'phone_number']

class OrderItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItems
        fields = ['pills', 'quantity', 'price']

class CreateOrderSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True)
    telegram_user_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = Order
        fields = [
            'telegram_user_id',
            'total_amount', 'status', 'is_chat',
            'delivery_method', 'payment_method',
            'branch', 'delivery_latitude', 'delivery_longitude',
            'delivery_price', 'items'
        ]

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required.")
        return value

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        telegram_user_id = validated_data.pop('telegram_user_id')

        try:
            telegram_user = TelegramUser.objects.get(id=telegram_user_id)
        except TelegramUser.DoesNotExist:
            raise serializers.ValidationError("Telegram foydalanuvchisi topilmadi.")

        order = Order.objects.create(user=telegram_user, **validated_data)
        for item_data in items_data:
            OrderItems.objects.create(order=order, **item_data)
        return order
