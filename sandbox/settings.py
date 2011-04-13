import sys, os

DEBUG = True
TEMPLATE_DEBUG = DEBUG   


ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

# add fulcrum
sys.path.insert(0, os.path.join(BASE_PATH, '../'))

DATABASES = {
    'default': {
        'ENGINE': 'sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': os.path.join(BASE_PATH, 'db'),                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

SITE_ID = 1

TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
USE_I18N = True
USE_L10N = True

# Media
MEDIA_ROOT = ''
MEDIA_URL = os.path.join(BASE_PATH, 'media/')
ADMIN_MEDIA_PREFIX = '/admin_media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '*y0zhxed0jmq9@0sijltfg!)_eng5^p=spya(@*3$t6of)y39%'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'sandbox.urls'

TEMPLATE_DIRS = (
    os.path.join(BASE_PATH, 'templates'),
    
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    #'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.markup',
    'sandbox.blog',
    'fulcrum',
)

FIXTURE_DIRS = (
    os.path.join(BASE_PATH, 'fixtures'),
)

APPEND_SLASH = False
