from .check_perform_transaction import CheckPerformTransaction
from .create_transaction import CreateTransaction
from .perform_transaction import PerformTransaction
from .cancel_transaction import CancelTransaction
from .check_transaction import CheckTransaction
from .get_statement import GetStatement

PAYME_AVAILABLE_METHODS = {
    "CheckPerformTransaction": CheckPerformTransaction,
    "CreateTransaction": CreateTransaction,
    "PerformTransaction": PerformTransaction,
    "CancelTransaction": CancelTransaction,
    "CheckTransaction": CheckTransaction,
    "GetStatement": GetStatement

}