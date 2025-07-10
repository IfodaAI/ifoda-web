import os
import uuid
from dotenv import load_dotenv
from django.conf import settings
load_dotenv()


async def upload_image(file_obj, file_name):
    try:
        file_extension = file_name.split('.')[-1]
        unique_file_name = f"{uuid.uuid4()}.{file_extension}"
        media_path = os.path.join(settings.MEDIA_ROOT, unique_file_name)

        with open(media_path, 'wb+') as destination:
            for chunk in file_obj.chunks():
                destination.write(chunk)

        image_url = f"{settings.MEDIA_URL}{unique_file_name}"
        return image_url
    except Exception as e:
        print(f"Failed to upload image to media folder: {str(e)}")
        return ''