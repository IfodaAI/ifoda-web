from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from ..payme.methods import PAYME_AVAILABLE_METHODS, PerformTransaction
from payme.permissions.payme_auth_permission import PaymeAuthPermission
from payme.permissions.payme_method_required_permission import PaymeMethodRequiredPermission
from app.models import Order
from ..payme.methods import CancelTransaction


class PaymeMerchantAPI(GenericAPIView):
    permission_classes = [PaymeAuthPermission, PaymeMethodRequiredPermission]

    def post(self, request, *args, **kwargs):
        payme_method = PAYME_AVAILABLE_METHODS[request.data.get("method")]()  # create instance of method
        order_id, action = payme_method(request.data.get("params"))  # __call__ method will be called
        return Response(data=action)
