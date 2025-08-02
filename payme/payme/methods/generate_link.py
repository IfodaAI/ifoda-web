import base64
from decimal import Decimal
from dataclasses import dataclass

from django.conf import settings
from dotenv import load_dotenv
import os


@dataclass
class GeneratePayLink:

    order_id: str
    amount: Decimal

    def generate_link(self,return_url) -> str:
        load_dotenv()
        generated_pay_link: str = "{payme_url}/{encode_params}"
        params: str = 'm={payme_id};ac.{payme_account}={order_id};a={amount};authorization=HJX&ESmd&ZJbZgGjuYii0uXMePcuuoHSVBN?'#;c={return_url}

        params = params.format(
            payme_id=os.getenv("PAYME_ID"),
            payme_account=os.getenv("PAYME_ACCOUNT"),
            order_id=self.order_id,
            amount=float(self.amount)*100,
            return_url=return_url
        )
        encode_params = base64.b64encode(params.encode("utf-8"))
        print('link_params: ',params)
        return generated_pay_link.format(
            payme_url=os.getenv("PAYME_URL"),
            encode_params=str(encode_params, 'utf-8')
        )
