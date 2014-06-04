from datetime import timedelta
import os

BROKER_URL = os.environ.get('REDISCLOUD_URL') + '/0'

CELERYBEAT_SCHEDULE = {
    'runs-every-5-minutes': {
        'task': 'tasks.fetch_treasuries',
        'schedule': timedelta(minutes=5),
    }
}

CELERY_ANNOTATIONS = {
    '*': {
        'rate_limit': '4/m',
    }
}
