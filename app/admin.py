from django.contrib import admin
from .models import TelegramUser,Branch,Pills,Payment,Order
# Test commit
admin.site.register(TelegramUser)
admin.site.register(Branch)
admin.site.register(Pills)
admin.site.register(Payment)
admin.site.register(Order)