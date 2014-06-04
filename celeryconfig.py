from datetime import timedelta

BROKER_URL = 'redis://localhost:6379/0'

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
