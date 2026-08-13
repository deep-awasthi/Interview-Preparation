"""ASGI config for Aether project."""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aether.config.settings")
application = get_asgi_application()
