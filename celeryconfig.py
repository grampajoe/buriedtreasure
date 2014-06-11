from datetime import timedelta
import os

from kombu import Queue

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
    'runs-every-5-minutes': {
        'task': 'tasks.fetch_listings',
        'schedule': timedelta(minutes=5),
    },
    'process-listings-every-5-minutes': {
        'task': 'tasks.process_listings',
        'schedule': timedelta(minutes=5),
    }
}

CELERY_ANNOTATIONS = {
    'tasks.fetch_detail': {
        'rate_limit': '5/m',
    }
}
