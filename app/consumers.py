from channels.db import database_sync_to_async
from asgiref.sync import sync_to_async
import json
from channels.generic.websocket import AsyncWebsocketConsumer
import requests
from dotenv import load_dotenv
import os
from django.utils.timezone import localtime
from django.core.serializers.json import DjangoJSONEncoder

@database_sync_to_async
def get_telegram_id(order_id):
    from .models import Order
    try:
        order = Order.objects.get(id=order_id)
        return order.user.telegram_id
    except Order.DoesNotExist:
        return None


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.order_id = self.scope['url_route']['kwargs']['order_id']
        self.room_group_name = f'chat_{self.order_id}'
        print('connect',self.room_group_name)
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Guruhdan chiqish
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data=None, bytes_data=None):
        from .models import Messages, Order
        data = json.loads(text_data)
        message = data.get('message', None)
        sender = data.get('sender', 'USER')
        message_type = data.get('type', 'TEXT')
        image_url = data.get('image', None)


        # Ma'lumotlarni bazaga saqlash
        order = await sync_to_async(Order.objects.get)(id=self.order_id)
        new_message = await sync_to_async(Messages.objects.create)(
            order=order,
            sender=sender,
            text=message,
            type=message_type,
            image_url=image_url
        )
        load_dotenv()
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        chat_id = await get_telegram_id(self.order_id)
        try:
            if message_type == 'IMAGE':
                requests.post(
                    url=f'https://api.telegram.org/bot{bot_token}/sendPhoto',
                    data={
                        'chat_id': chat_id,
                        'photo': image_url
                    }
                )
            elif message_type == 'TEXT':
                requests.post(
                    url=f'https://api.telegram.org/bot{bot_token}/sendMessage',
                    data={
                        'chat_id': chat_id,
                        'text': message,
                    }
                )
            else:
                requests.post(
                    url=f'https://api.telegram.org/bot{bot_token}/sendMessage',
                    data={
                        'chat_id': chat_id,
                        'text': 'Xabar turi noto\'g\'ri',
                    }
                )
        except Exception as e:
            print(f"Failed to send message to Telegram: {str(e)}")

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_type': message_type,
                'message': message,
                'sender': sender,
                'image_url': image_url,
                'timestamp': str(new_message.timestamp)
            }
        )

    async def chat_message(self, event):
        print('chat_message',event)
        message = event.get('message', None)
        sender = event['sender']
        message_type = event.get('message_type', 'TEXT')
        image_url = event.get('image_url', None)

        await self.send(text_data=json.dumps({
            'message': message,
            'sender': sender,
            'type': message_type,
            'image_url': image_url,
            'timestamp': event['timestamp']
        }))

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_name = "notifications"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notify(self, event):
        newChat = event.get("newChat", True)
        await self.send(text_data=json.dumps({"newChat": newChat}))

class NewChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.order_id = self.scope['url_route']['kwargs']['order_id']
        self.room_group_name = f'chat_{self.order_id}'

        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        message_type = data.get('type', 'TEXT')
        sender = data.get('sender')
        text = data.get('text', '')

        message = await self.save_message(
            order_id=self.order_id,
            message_type=message_type,
            sender=sender,
            text=text
        )#TODO

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': {
                    'id': str(message.id),
                    'type': message.type,
                    'sender': message.sender,
                    'status': message.status,
                    'text': message.text,
                    'image': message.image,
                    'timestamp': localtime(message.timestamp).isoformat()
                }
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event['message'], cls=DjangoJSONEncoder))

    @database_sync_to_async
    def save_message(self, order_id, message_type, sender, text=''):
        from .models import Messages, Order
        order = Order.objects.get(id=order_id)
        return Messages.objects.create(
            order=order,
            type=message_type,
            sender=sender,
            text=text
        )
