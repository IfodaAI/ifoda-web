import base64

import binascii
from django.conf import settings
from rest_framework.permissions import BasePermission

from payme.payme.status.exceptions import PermissionDenied
from payme.utils.logging import logger

from dotenv import load_dotenv
import os
load_dotenv()


class PaymeAuthPermission(BasePermission):

    def has_permission(self, request, view):
        is_payme = False
        password = request.META.get('HTTP_AUTHORIZATION')
        if not isinstance(password, str):
            error_message = "Request from an unauthorized source!"
            logger.error(error_message)
            raise PermissionDenied(error_message=error_message)

        password = password.split()[-1]

        try:
            password = base64.b64decode(password).decode('utf-8')
        except (binascii.Error, UnicodeDecodeError) as error:
            error_message = "Error when authorize request to merchant!"
            logger.error(error_message)

            raise PermissionDenied(error_message=error_message) from error

        merchant_key = password.split(':')[-1]

        if merchant_key == os.getenv("PAYME_KEY"):
            is_payme = True

        if merchant_key != os.getenv("PAYME_KEY"):
            logger.error("Invalid key in request!")

        if is_payme is False:
            raise PermissionDenied(
                error_message="Unavailable data for unauthorized users!"
            )

        return True
