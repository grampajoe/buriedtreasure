import os
from datetime import timedelta

from kombu import Queue


broker_url = os.environ.get('CLOUDAMQP_URL')
broker_use_ssl = False

# Handle ampqs://
if broker_url is not None and broker_url.startswith('amqps://'):
    broker_url = broker_url.replace('amqps://', 'amqp://', 1)
    broker_use_ssl = True

task_default_queue = 'default'
task_default_exchange = 'tasks'
task_default_exchange_type = 'topic'
task_default_routing_key = 'default'

task_queues = (
    Queue('default', routing_key='default'),
    Queue('fetch_detail', routing_key='fetch_detail'),
)

task_routes = {
    'tasks.fetch_detail': {
        'queue': 'fetch_detail',
        'routing_key': 'fetch_detail',
    },
}

beat_schedule = {
    'fetch_listings': {
        'task': 'tasks.fetch_listings',
        'schedule': timedelta(minutes=5),
    },
    'scrub_scrubs': {
        'task': 'tasks.scrub_scrubs',
        'schedule': timedelta(minutes=1),
    },
}

task_annotations = {
    'tasks.fetch_detail': {
        'rate_limit': os.environ.get('FETCH_DETAIL_RATE', '5/m'),
    }
}
