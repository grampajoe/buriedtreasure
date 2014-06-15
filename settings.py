import os
import urlparse

SECRET_KEY = os.environ.get('SECRET_KEY', 'butt')

API_SERVER = 'https://openapi.etsy.com/v2/'
ETSY_SERVER = 'http://etsy.com/'
ETSY_API_KEY = os.environ.get('ETSY_API_KEY')
ETSY_API_SECRET = os.environ.get('ETSY_API_SECRET')

REDIS_CONFIG = urlparse.urlparse(os.environ.get('REDISCLOUD_URL'))
