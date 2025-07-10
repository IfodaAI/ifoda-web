from ..models import PaymeMerchantTransaction
from django.conf import settings
from rest_framework import serializers
from ..utils.logging import logger
from ..utils.get_params import get_params
from payme.payme.status.exceptions import IncorrectAmount
from payme.payme.status.exceptions import PerformTransactionDoesNotExist
from app.models import Order
from dotenv import load_dotenv
import os
load_dotenv()


class PaymeTransactionSerializer(serializers.ModelSerializer):
    start_date = serializers.IntegerField(allow_null=True)
    end_date = serializers.IntegerField(allow_null=True)

    class Meta:
        model = PaymeMerchantTransaction
        fields = '__all__'
        extra_fields = ['start_date', 'end_date']

    def validate(self, attrs) -> dict:

        if attrs.get("order_id") is not None:
            try:
                order = Order.objects.get(
                    id=attrs['order_id']
                )
                print("amount: ",order.total_amount, attrs['amount']/100, float(order.total_amount) != float(int(attrs['amount'])/100))
                if float(order.total_amount) != float(int(attrs['amount'])/100):
                    raise IncorrectAmount()

            except IncorrectAmount as error:
                logger.error("Invalid amount for order: %s", attrs['order_id'])
                raise IncorrectAmount() from error

        return attrs

    def validate_amount(self, amount: int) -> int:
        if amount is not None:
            if amount <= int(os.getenv("PAYME_MIN_AMOUNT")):
                raise IncorrectAmount("Payment amount is less than allowed.")

        return amount

    def validate_order_id(self, order_id) -> int:
        try:
            Order.objects.get(id=order_id)
        except Order.DoesNotExist as error:
            logger.error("Order does not exist order_id: %s", order_id)
            raise PerformTransactionDoesNotExist() from error

        return order_id

    @staticmethod
    def get_validated_data(params: dict) -> dict:
        serializer = PaymeTransactionSerializer(
            data=get_params(params)
        )
        serializer.is_valid(raise_exception=True)
        clean_data: dict = serializer.validated_data

        return clean_data
