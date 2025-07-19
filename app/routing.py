from django.urls import path,re_path
from . import consumers

websocket_urlpatterns = [
    # path('ws/chat/<str:order_id>/', consumers.ChatConsumer.as_asgi()),
    path('ws/notification/', consumers.NotificationConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<order_id>[0-9a-f-]+)/$', consumers.NewChatConsumer.as_asgi()),
]