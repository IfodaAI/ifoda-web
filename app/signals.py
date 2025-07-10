from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from .models import Payment
from .telegram_notify import send_telegram_notification

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        token = Token.objects.create(user=instance)
        print(f"Token created for user {instance.phone_number}: {token.key}")

@receiver(post_save, sender=Payment)
def payment_completed_handler(sender, instance, created, **kwargs):
    if not created:
        old_instance = sender.objects.get(pk=instance.pk)
        send_telegram_notification(
            "📦 Sizning filialingizga *yangi buyurtma* keldi.\nBatafsil maʼlumotni Logix orqali ko‘rishingiz mumkin.",1330892088
        )
        # if old_instance.payment_status != 'completed' and instance.payment_status == 'completed':
            # Telegramga xabar yuborish