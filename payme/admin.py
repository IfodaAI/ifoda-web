from django.contrib import admin
from .models import PaymeMerchantTransaction


@admin.register(PaymeMerchantTransaction)
class PaymeMerchantTransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'order_id', 'amount', 'state', 'created_at']

