import uuid
import time
import datetime
from datetime import datetime
from typing import Tuple, Any, Dict
from app.models import Order, Payment

import requests
import json
from dotenv import load_dotenv
import os
from payme.utils.logging import logger
from payme.utils.get_params import get_params
from payme.models import PaymeMerchantTransaction
from ..status.exceptions import TooManyRequests
from payme.serializers.payme_transaction_serializer import PaymeTransactionSerializer


class CreateTransaction:

    def __call__(self, params: Dict) -> Tuple[Any, Dict]:
        serializer = PaymeTransactionSerializer(data=get_params(params))
        serializer.is_valid(raise_exception=True)
        order_id = serializer.validated_data.get("order_id")

        try:
            transaction = PaymeMerchantTransaction.objects.filter(
                order_id=order_id
            ).order_by('created_at').last()

            if transaction is not None:
                if transaction._id != serializer.validated_data.get("_id"):
                    raise TooManyRequests()

        except TooManyRequests as error:
            logger.error("Too many requests for transaction %s", error)
            raise TooManyRequests() from error

        if transaction is None:
            transaction = PaymeMerchantTransaction.objects.create(
                _id=serializer.validated_data.get('_id'),
                order_id=serializer.validated_data.get('order_id'),
                transaction_id=uuid.uuid4(),
                amount=serializer.validated_data.get('amount'),
                created_at_ms=int(time.time() * 1000),
            )

        if transaction:
            response: dict = {
                "result": {
                    "create_time": int(transaction.created_at_ms),
                    "transaction": transaction.transaction_id,
                    "state": int(transaction.state),
                }
            }

        return order_id, response

    @staticmethod
    def _convert_ms_to_datetime(time_ms: str) -> datetime:
        readable_datetime = datetime.datetime.fromtimestamp(time_ms / 1000)

        return readable_datetime
