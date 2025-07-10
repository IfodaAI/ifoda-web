from django.urls import path
from .api.payme_merchant_api import PaymeMerchantAPI


urlpatterns = [
    path('merchant/', PaymeMerchantAPI.as_view(), name='payme-merchant'),
]