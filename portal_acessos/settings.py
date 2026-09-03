"""Configurações do Portal de Acessos.

Para produção, configure SECRET_KEY, DEBUG=False, ALLOWED_HOSTS e HTTPS por variáveis
de ambiente, sem versionar segredos.
"""
from pathlib import Path
from decouple import config
import os

import ldap
from django_auth_ldap.config import LDAPSearch


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "").split(",")
    if host.strip()
]

CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "usuarios",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    'usuarios.middleware.ExigeTrocaSenhaMiddleware',
]

ROOT_URLCONF = "portal_acessos.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "portal_acessos.wsgi.application"
ASGI_APPLICATION = "portal_acessos.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("POSTGRES_DB"),
        "USER": config("POSTGRES_USER"),
        "PASSWORD": config("POSTGRES_PASSWORD"),
        "HOST": config("POSTGRES_HOST", default="localhost"),
        "PORT": config("POSTGRES_PORT", default="5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Deve ser definido antes de criar a primeira migration.
AUTH_USER_MODEL = "usuarios.Funcionario"

# --- Autenticação híbrida: Active Directory (LDAP) + local ---
# A vinculação ao AD é opcional por colaborador (campo Funcionario.vinculado_ad).
# LDAPBackend só autentica quem estiver vinculado; os demais seguem o fluxo de
# senha local de sempre via ModelBackend.
AUTH_LDAP_SERVER_URI = f"ldap://{config('LDAP_SERVER')}"
AUTH_LDAP_START_TLS = True

AUTH_LDAP_BIND_DN = config("LDAP_BIND_USER")
AUTH_LDAP_BIND_PASSWORD = config("LDAP_BIND_PASSWORD")

AUTH_LDAP_USER_SEARCH = LDAPSearch(
    config("LDAP_BASE_DN"),
    ldap.SCOPE_SUBTREE,
    "(sAMAccountName=%(user)s)",
)

# Impede que o LDAPBackend crie usuários novos automaticamente — o vínculo com
# o AD (campo vinculado_ad) é decidido no cadastro/edição do colaborador.
AUTH_LDAP_NO_NEW_USERS = True
AUTH_LDAP_ALWAYS_UPDATE_USER = False

AUTH_LDAP_CONNECTION_OPTIONS = {
    ldap.OPT_REFERRALS: 0,
    # TODO: o DC apresenta um certificado não confiável para o container
    # (falha "unable to get local issuer certificate"). Ideal é importar o
    # certificado da CA interna e trocar por OPT_X_TLS_CACERTFILE. Por ora,
    # a validação do certificado do STARTTLS está desativada.
    ldap.OPT_X_TLS_REQUIRE_CERT: ldap.OPT_X_TLS_NEVER,
    ldap.OPT_X_TLS_NEWCTX: 0,
}

AUTHENTICATION_BACKENDS = [
    "usuarios.auth_backends.LDAPBackend",
    "django.contrib.auth.backends.ModelBackend",
]

LOGIN_URL = "usuarios:login"
LOGIN_REDIRECT_URL = "usuarios:home"
LOGOUT_REDIRECT_URL = "usuarios:login"

SESSION_EXPIRE_AT_BROWSER_CLOSE = True
