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
        'rate_limit': '10/m',
    }
}
