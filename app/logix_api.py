import requests


def logix_post(branch_id, product_id, quantity, price):
    # url = "http://94.141.76.204:3456/LogiXWEBAPI/post/sales"
    url = "http://192.168.0.172:3456/LogiXWEBAPI/post/sales"
    headers = {
        'Authorization': 'frEswo1ihIv3qiT9oc8ebrOThAZi0a',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    data = {
        "branch_id": branch_id,
        "product_id": product_id,
        "quantity": quantity,
        "price": price
    }

    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()
        return None
