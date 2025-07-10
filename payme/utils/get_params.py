from django.conf import settings

from dotenv import load_dotenv
import os
load_dotenv()


def get_params(params: dict) -> dict:
    account: dict = params.get("account")
    print('account', account, account is not None)

    clean_params: dict = {"_id": params.get("id"), "time": params.get("time"), "amount": params.get("amount"),
                          "reason": params.get("reason"), "start_date": params.get("from"),
                          "end_date": params.get("to")}

    if account is not None:
        account_name: str = str(os.getenv("PAYME_ACCOUNT"))
        clean_params["order_id"] = account['order_id']

    return clean_params
