from django.urls import re_path
from .consumers import CodeEditorRoom  # Import your WebSocket consumer

websocket_urlpatterns = [
    re_path(r"ws/chat/(?P<room_id>\w+)/$", CodeEditorRoom.as_asgi()),
]
