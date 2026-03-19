from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# ── SEGURANÇA ────────────────────────────────────────────────────────────────
SECRET_KEY = os.getenv('DJANGO_SECRET')

AUTH_USER_MODEL = 'app.CustomUser'

# Produção: DEBUG DEVE ser False. Para desenvolvimento local, defina DEBUG=True no .env
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# Defina os hosts reais em produção (ex: meudominio.com, 192.168.1.10)
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '127.0.0.1,localhost,felipecell.squareweb.app').split(',')

# CSRF: lista de origens confiáveis para requisições POST (necessário com HTTPS)
CSRF_TRUSTED_ORIGINS = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://127.0.0.1,http://localhost,https://felipecell.squareweb.app').split(',')

# ── APPS ─────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'cloudinary',
    'cloudinary_storage',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'app',
]

# ── MIDDLEWARE ────────────────────────────────────────────────────────────────
# CORRIGIDO: SessionMiddleware estava duplicado (bug de segurança/performance)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# ── BANCO DE DADOS ────────────────────────────────────────────────────────────
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# ── VALIDAÇÃO DE SENHAS ───────────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── INTERNACIONALIZAÇÃO ───────────────────────────────────────────────────────
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# ── ARQUIVOS ESTÁTICOS ────────────────────────────────────────────────────────
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # necessário para collectstatic em produção
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── AUTENTICAÇÃO ──────────────────────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/home/'
LOGOUT_REDIRECT_URL = '/login/'

# ── ALLAUTH / GOOGLE OAUTH ────────────────────────────────────────────────────
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': os.environ.get('GOOGLE_ID'),
            'secret': os.environ.get('GOOGLE_SECRET'),
            'key': ''
        },
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
    }
}

# CORRIGIDO: SOCIALACCOUNT_LOGIN_ON_GET=True permite CSRF login via GET request.
# Com False, o login social exige um POST com token CSRF.
SOCIALACCOUNT_LOGIN_ON_GET = False

ACCOUNT_EMAIL_VERIFICATION = "none"

# ── CLOUDINARY ────────────────────────────────────────────────────────────────
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.getenv('CLOUDINARY_NAME'),
    'API_KEY': os.getenv('CLOUDINARY_API'),
    'API_SECRET': os.getenv('CLOUDINARY_SECRET'),
}
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

# ── HEADERS DE SEGURANÇA HTTP ─────────────────────────────────────────────────
# Ativados apenas em produção (DEBUG=False) para não quebrar desenvolvimento local
if not DEBUG:
    # A Square Cloud já faz SSL termination no proxy.
    # NÃO use SECURE_SSL_REDIRECT, pois causa loop infinito de redirecionamento.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_HSTS_SECONDS = 31536000          # 1 ano
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

    # Cookies de sessão e CSRF via HTTPS apenas
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# Proteções válidas tanto em dev quanto em produção
SESSION_COOKIE_HTTPONLY = True      # JS não acessa o cookie de sessão (anti-XSS)
CSRF_COOKIE_HTTPONLY = True         # Mesmo para CSRF
X_FRAME_OPTIONS = 'DENY'           # Bloqueia clickjacking (iframe)
SECURE_CONTENT_TYPE_NOSNIFF = True  # Bloqueia MIME sniffing
SECURE_BROWSER_XSS_FILTER = True    # Header X-XSS-Protection legado

# Tempo de vida da sessão: expira ao fechar o browser (boa prática para apps internos)
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 28800  # 8 horas máximo

# ── WEBHOOK SECRET TOKEN ──────────────────────────────────────────────────────
# Token secreto para autenticar chamadas do bot ao endpoint /api/webhook/
WEBHOOK_SECRET_TOKEN = os.getenv('WEBHOOK_SECRET_TOKEN', '')

SITE_ID = 1
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
