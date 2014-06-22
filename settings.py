import os
import urlparse
from datetime import timedelta

from kombu import Queue


SECRET_KEY = os.environ.get('SECRET_KEY', 'butt')

API_SERVER = 'https://openapi.etsy.com/v2/'
ETSY_SERVER = 'http://etsy.com/'
ETSY_API_KEY = os.environ.get('ETSY_API_KEY')
ETSY_API_SECRET = os.environ.get('ETSY_API_SECRET')

REDIS_CONFIG = urlparse.urlparse(os.environ.get('REDISCLOUD_URL'))

BROKER_URL = os.environ.get('RABBITMQ_BIGWIG_URL')

CELERY_DEFAULT_QUEUE = 'default'
CELERY_DEFAULT_EXCHANGE = 'tasks'
CELERY_DEFAULT_EXCHANGE_TYPE = 'topic'
CELERY_DEFAULT_ROUTING_KEY = 'default'

CELERY_QUEUES = (
    Queue('default', routing_key='default'),
    Queue('fetch_detail', routing_key='fetch_detail'),
)

CELERY_ROUTES = {
    'tasks.fetch_detail': {
        'queue': 'fetch_detail',
        'routing_key': 'fetch_detail',
    },
}

CELERYBEAT_SCHEDULE = {
    'fetch_listings': {
        'task': 'tasks.fetch_listings',
        'schedule': timedelta(minutes=5),
    },
    'process_listings': {
        'task': 'tasks.process_listings',
        'schedule': timedelta(minutes=2, seconds=30),
    },
    'scrub_scrubs': {
        'task': 'tasks.scrub_scrubs',
        'schedule': timedelta(minutes=1),
    },
}

CELERY_ANNOTATIONS = {
    'tasks.fetch_detail': {
        'rate_limit': os.environ.get('FETCH_DETAIL_RATE', '10/m'),
    }
}

# These Buried Treasure settings come from the environment, so you know they're
# good for you.

# Score multiplier for user count
BT_USER_WEIGHT = int(os.environ.get('BT_USER_WEIGHT', 100))

# Score bonus added if gold is in the materials
BT_GOLD_BONUS = int(os.environ.get('BT_GOLD_BONUS', 5000))

# Number of low user count listing ids preserved when scrubbing scrubs
BT_SCRUB_LIMIT = int(os.environ.get('BT_SCRUB_LIMIT', 5000))

# Number of listing records to get at a time
BT_CHUNK_SIZE = int(os.environ.get('BT_CHUNK_SIZE', 50))

# Number of listings to keep data for
BT_LISTING_LIMIT = int(os.environ.get('BT_LISTING_LIMIT', 500))
