"""Configuração WSGI do projeto Portal de Acessos."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "portal_acessos.settings")

application = get_wsgi_application()
