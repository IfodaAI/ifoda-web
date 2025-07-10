from rest_framework.permissions import BasePermission
from payme.payme.methods import PAYME_AVAILABLE_METHODS
from payme.payme.status.exceptions import MethodNotFound


class PaymeMethodRequiredPermission(BasePermission):

    def has_permission(self, request, view):
        payme_method = request.data.get("method")

        if payme_method not in PAYME_AVAILABLE_METHODS.keys():
            raise MethodNotFound(f"Unavailable method: {payme_method}")

        return True
