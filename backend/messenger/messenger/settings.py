from enum import verify
from pathlib import Path
import os
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Загрузка .env файла
dotenv_path = os.path.join(BASE_DIR, '.env')
load_dotenv(dotenv_path)

SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'  # Исправлено для булевого значения

# Database
DB_HOST = os.environ.get('DB_HOST')
DB_PORT = os.environ.get('DB_PORT')
DB_NAME = os.environ.get('DB_NAME')
DB_SCHEMA = os.environ.get('DB_SCHEMA')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')

# MinIO настройки
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
MINIO_USE_HTTPS = False
MINIO_MEDIA_BUCKET_NAME = os.getenv('MINIO_MEDIA_BUCKET_NAME', 'django-media')
MINIO_STATIC_BUCKET_NAME = os.getenv('MINIO_STATIC_BUCKET_NAME', 'django-static')
MINIO_EXTERNAL_ENDPOINT = os.getenv('MINIO_EXTERNAL_ENDPOINT', MINIO_ENDPOINT)

ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'test-vapp-03.sgp.ru',
                 'sco1-vapp-04.sgp.ru', '0.0.0.0', 'sco1-vapp-09.sgp.ru']

# Application definition
INSTALLED_APPS = [
    'channels',
    'daphne',
    'corsheaders',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'api.apps.ApiConfig',
]

# Добавьте 'storages' после staticfiles
INSTALLED_APPS.insert(INSTALLED_APPS.index('django.contrib.staticfiles') + 1, 'storages')

# Channels
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

ASGI_APPLICATION = 'messenger.asgi.application'
WSGI_APPLICATION = 'messenger.wsgi.application'

# CORS
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    'https://sco1-vapp-09.sgp.ru',
    'http://localhost:3000',
    'http://83.222.9.213:6767',
    'ws://localhost:3000',
    'ws://83.222.9.213:6767',
]

CSRF_TRUSTED_ORIGINS = ['https://sco1-vapp-09.sgp.ru']

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'api.middleware.RemoteUserMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'api.backends.RemoteUserBackend',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.RemoteUserAuthentication',
    ],
}

USE_X_FORWARDED_HOST = True
REMOTE_USER_HEADER = 'HTTP_REMOTE_USER'

ROOT_URLCONF = 'messenger.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
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

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'options': '-c search_path=' + DB_SCHEMA,
        },
        'NAME': DB_NAME,
        'USER': DB_USER,
        'PASSWORD': DB_PASSWORD,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'ru-RU'
TIME_ZONE = 'Asia/Yekaterinburg'
USE_I18N = True
USE_TZ = False

# Static files
STATIC_URL = '/messenger/api/static/'
STATIC_ROOT = os.path.join(os.path.join(BASE_DIR, 'staticfiles'))
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static')
]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Media files configuration
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')  # Локальная папка для fallback

# Создаем директорию если не существует
if not os.path.exists(MEDIA_ROOT):
    os.makedirs(MEDIA_ROOT)

# STORAGES configuration - ВАЖНО: используем новую структуру Django 4.2+
STORAGES = {
    "default": {
        "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
        "OPTIONS": {
            "bucket_name": MINIO_MEDIA_BUCKET_NAME,
            "access_key": MINIO_ACCESS_KEY,
            "secret_key": MINIO_SECRET_KEY,
            "endpoint_url": f"http://{MINIO_ENDPOINT}",
            "use_ssl": False,
            "verify": False,
            "file_overwrite": False,
            "querystring_auth": True,  # подписанные URL для приватных файлов
            "querystring_expire": 3600,  # срок жизни URL (1 час)
            "default_acl": "public-read",
            "custom_domain": f"{MINIO_EXTERNAL_ENDPOINT}/{MINIO_MEDIA_BUCKET_NAME}",
            "location": "",  # Корень бакета
            "signature_version": "s3v4",
            "addressing_style": "path",  # Или "virtual" в зависимости от MinIO
        },
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        # Или используйте MinIO для статики:
        # "BACKEND": "storages.backends.s3.S3Storage",
        # "OPTIONS": {
        #     "bucket_name": MINIO_STATIC_BUCKET_NAME,
        #     "access_key": MINIO_ACCESS_KEY,
        #     "secret_key": MINIO_SECRET_KEY,
        #     "endpoint_url": f"http{'s' if MINIO_USE_HTTPS else ''}://{MINIO_ENDPOINT}",
        #     "default_acl": "public-read",
        #     "querystring_auth": False,
        #     "location": "static",
        # },
    },
}

# Media URL - исправленный вариант
if MINIO_EXTERNAL_ENDPOINT:
    # Убираем лишний слеш в конце bucket_name
    MEDIA_URL = f"http://{MINIO_EXTERNAL_ENDPOINT}/{MINIO_MEDIA_BUCKET_NAME}/"
else:
    MEDIA_URL = f"http://{MINIO_ENDPOINT}/{MINIO_MEDIA_BUCKET_NAME}/"