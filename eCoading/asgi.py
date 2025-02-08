import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eCoading.settings")
django.setup()  # Ensure Django settings are loaded

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from Room.routing import websocket_urlpatterns  # Import WebSocket URLs

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
