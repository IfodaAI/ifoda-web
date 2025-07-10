import json


def to_json(**kwargs) -> str:
    """
    Use this static method to data dumps.
    """
    data: dict = {
        "method": kwargs.pop("method"),
        "params": kwargs.pop("params"),
    }

    return json.dumps(data)
