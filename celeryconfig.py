from datetime import timedelta
import os

BROKER_URL = os.environ.get('RABBITMQ_BIGWIG_URL')

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
        'rate_limit': '4/m',
    }
}
