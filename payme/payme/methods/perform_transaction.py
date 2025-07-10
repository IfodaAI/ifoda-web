import time
from typing import Any, Dict, Tuple

from django.db import DatabaseError
from app.models import Order, Payment, OrderItems
from app.logix_api import logix_post
import requests
import json
from dotenv import load_dotenv
import os

from payme.payme.status.status import CLOSE_TRANSACTION
from payme.utils.logging import logger
from payme.utils.get_params import get_params
from payme.models import PaymeMerchantTransaction
from payme.serializers.payme_transaction_serializer import PaymeTransactionSerializer


class PerformTransaction:
    def __call__(self, params: Dict) -> Tuple[Any, Dict]:

        serializer = PaymeTransactionSerializer(data=get_params(params))
        serializer.is_valid(raise_exception=True)
        clean_data: dict = serializer.validated_data
        response: dict
        transaction: PaymeMerchantTransaction

        try:
            transaction = PaymeMerchantTransaction.objects.get(_id=clean_data.get("_id"))
            transaction.state = CLOSE_TRANSACTION
            if transaction.perform_time == 0:
                transaction.perform_time = int(time.time() * 1000)

            transaction.save()

            print('PerformTransaction:', transaction.state, transaction.state != 2)
            order = Order.objects.get(id=transaction.order_id)
            load_dotenv()
            bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = order.user.telegram_id
            language = order.user.language.name
            order.status = 'COMPLETED'
            order.save()
            try:
                payment_exists = Payment.objects.filter(order=order).exists()
                if not payment_exists:
                    Payment.objects.create(
                        order=order,
                        payment_method='payMe',
                        amount=order.total_amount,
                        payment_status='completed'
                    )
            except Exception as error:
                print('Paymeda payment yaartishda xatolik yuz berdi: ', error)

            if language == 'uz':
                # text = 'To\'lov muvaffaqiyatli amalga oshildi ✅'
                text = """To'lov muvaffaqiyatli amalga oshildi ✅
Buyurtma 24 soat ichida yetkazib beriladi.
Ishonchingiz uchun minnatdormiz
IFODA kompaniyasini tanlaganingizdan mamnunmiz
Birgalikda yetishtiramiz!
✅"""
                keyword_text = 'Yangi Buyurtma'
            elif language == 'ru':
                text = 'Платеж прошел успешно ✅'
                keyword_text = 'Новый Заказ'
            else:
                text = 'The payment was successfully ✅'
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

            try:
                order_items = OrderItems.objects.filter(order__id=transaction.order_id)
                branch_id = order.branch.branch_id
                for item in order_items:
                    product_id = item.pills.product_id
                    quantity = item.quantity
                    price = item.price
                    if not item.pills.small_product:
                        res_logix = logix_post(branch_id=branch_id, product_id=product_id, quantity=quantity,
                                            price=float(price))
                        if not res_logix:
                            item.logix_status = 'ERROR'
            except Exception as e:
                print('LogiX apida xatolik: ', e)
            response: dict = {
                "result": {
                    "perform_time": int(transaction.perform_time),
                    "transaction": transaction.transaction_id,
                    "state": int(transaction.state),
                }
            }
        except DatabaseError as error:
            logger.error("error while getting transaction in db: %s", error)

        return transaction.order_id, response
