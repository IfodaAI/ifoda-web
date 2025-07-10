import time

from django.db import transaction
from app.models import Order
import requests
import json
from dotenv import load_dotenv
import os
from payme.utils.logging import logger
from payme.models import PaymeMerchantTransaction
from ..status.exceptions import PerformTransactionDoesNotExist
from payme.serializers.payme_transaction_serializer import PaymeTransactionSerializer


class CancelTransaction:

    @transaction.atomic
    def __call__(self, params: dict):
        clean_data: dict = PaymeTransactionSerializer.get_validated_data(
            params=params
        )
        try:
            with transaction.atomic():
                transactions = PaymeMerchantTransaction.objects.filter(_id=clean_data.get('_id')).first()
                if transactions.cancel_time == 0:
                    transactions.cancel_time = int(time.time() * 1000)
                if transactions.perform_time == 0:
                    transactions.state = -1
                if transactions.perform_time != 0:
                    transactions.state = -2
                transactions.reason = clean_data.get("reason")
                transactions.save()

                order = Order.objects.get(id=transactions.order_id)
                load_dotenv()
                bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
                chat_id = order.user.telegram_id
                language = order.user.language.name
                print('CancelTransaction:', transactions.state, transactions.state != 2)
                if transactions.state != 2:
                    order.status = 'IN_PAYMENT'
                    order.save()

                    if language == 'uz':
                        text = 'To\'lov bekor qilindi ❌'
                        keyword_text = 'Yangi Buyurtma'
                    elif language == 'ru':
                        text = 'Платеж отменен ❌'
                        keyword_text = 'Новый Заказ'
                    else:
                        text = 'Payment canceled ❌'
                        keyword_text = 'New Order'
                    reply_keyboard = {
                        "keyboard": [
                            [{"text": keyword_text}]
                        ],
                        "resize_keyboard": True,
                        "one_time_keyboard": True
                    }
                    try:
                        requests.post(
                            url=f'https://api.telegram.org/bot{bot_token}/sendMessage',
                            data={
                                'chat_id': chat_id,
                                'text': text,
                                'parse_mode': 'HTML',
                                'reply_markup': json.dumps(reply_keyboard)
                            }
                        ).json()
                    except Exception as e:
                        print('paymeda Telegramga xabar yuborishda xatolik yuz berdi: ', e)

        except PerformTransactionDoesNotExist as error:
            logger.error("Paycom transaction does not exist: %s", error)
            raise PerformTransactionDoesNotExist() from error

        response: dict = {
            "result": {
                "state": transactions.state,
                "cancel_time": transactions.cancel_time,
                "transaction": transactions.transaction_id,
                "reason": int(transactions.reason),
            }
        }

        return transactions.order_id, response
