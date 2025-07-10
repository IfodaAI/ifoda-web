from django.db import DatabaseError
from app.models import Order
from payme.utils.logging import logger
from payme.models import PaymeMerchantTransaction
from payme.serializers.payme_transaction_serializer import PaymeTransactionSerializer



class CheckTransaction:

    def __call__(self, params: dict) -> None:
        clean_data: dict = PaymeTransactionSerializer.get_validated_data(
            params=params
        )

        try:
            transaction = PaymeMerchantTransaction.objects.get(_id=clean_data.get("_id"), )
            response = {
                "result": {
                    "create_time": int(transaction.created_at_ms),
                    "perform_time": transaction.perform_time,
                    "cancel_time": transaction.cancel_time,
                    "transaction": transaction.transaction_id,
                    "state": transaction.state,
                    "reason": None,
                }
            }
            if transaction.reason is not None:
                response["result"]["reason"] = int(transaction.reason)

        except DatabaseError as error:
            logger.error("Error getting transaction in database: %s", error)

        return None, response
