"""
Django settings for easylearnsite project.
EasyLearnSite — игровая платформа для школьников 1-4 классов.
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Безопасность (для разработки) ---
SECRET_KEY = 'django-insecure-easylearn-CHANGE-ME-IN-PRODUCTION'
DEBUG = True
ALLOWED_HOSTS = ['*']


CSRF_TRUSTED_ORIGINS = [
    'https://*.ngrok-free.dev',
    'https://*.ngrok-free.app',
    'https://*.ngrok.io',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]


# --- Приложения ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # наши приложения
    'accounts',
    'games',
    'scores',
]


# --- Middleware ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# --- URLs / WSGI ---
ROOT_URLCONF = 'easylearnsite.urls'
WSGI_APPLICATION = 'easylearnsite.wsgi.application'


# --- Шаблоны ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


# --- База данных ---
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# --- Валидация паролей ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# --- Кастомная модель пользователя ---
AUTH_USER_MODEL = 'accounts.User'


# --- Язык и время ---
LANGUAGE_CODE = 'ru-ru'
TIME_ZONE = 'Asia/Bishkek'
USE_I18N = True
USE_TZ = True


# --- Статика ---
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'


# --- Медиа ---
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


# --- Авторизация ---
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'


# --- Прочее ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# --- Сообщения ---
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.DEBUG: 'debug',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'error',
}