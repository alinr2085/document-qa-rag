import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).lower() in ("1", "true", "yes", "on")


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")
CSRF_TRUSTED_ORIGINS = [
    o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "documents",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # admin theme override: templates/admin/base_site.html
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

if os.environ.get("DB_ENGINE", "sqlite").lower() == "oracle":
    # python-oracledb thin mode: no Oracle Client install needed
    # Django treats NAME as a SID when HOST/PORT are set. FREEPDB1 is a *service name*,
    # so HOST/PORT stay empty and NAME holds an Easy Connect string: host:port/service
    _host = os.environ.get("ORACLE_HOST", "oracle")
    _port = os.environ.get("ORACLE_PORT", "1521")
    _service = os.environ.get("ORACLE_SERVICE", "FREEPDB1")
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.oracle",
            "NAME": f"{_host}:{_port}/{_service}",
            "USER": os.environ.get("ORACLE_USER", "docqa"),
            "PASSWORD": os.environ.get("ORACLE_PASSWORD", "docqa_pass"),
            "HOST": "",
            "PORT": "",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": DATA_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "fa"
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "media/"
MEDIA_ROOT = DATA_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------- REST framework ----------
# API_REQUIRE_AUTH=true  -> API needs login (session or Basic auth)
_api_permission = (
    "rest_framework.permissions.IsAuthenticated"
    if env_bool("API_REQUIRE_AUTH", False)
    else "rest_framework.permissions.AllowAny"
)
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [_api_permission],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Document Q&A API",
    "DESCRIPTION": "سامانه پرسش و پاسخ از اسناد (Django + LangChain + Google Ai Studio / Gemini)",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # separate request/response schemas: upload fields become real file pickers
    # and read-only fields (id, created_at, ...) are no longer "required" in the form
    "COMPONENT_SPLIT_REQUEST": True,
}

# ---------- LLM / RAG ----------
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "60"))

RAG_CHUNK_SIZE = int(os.environ.get("RAG_CHUNK_SIZE", "800"))
RAG_CHUNK_OVERLAP = int(os.environ.get("RAG_CHUNK_OVERLAP", "120"))
RAG_TOP_K = int(os.environ.get("RAG_TOP_K", "4"))
# Optional extra LLM call that rewrites the question into a better search query
RAG_QUERY_REWRITE = env_bool("RAG_QUERY_REWRITE", False)