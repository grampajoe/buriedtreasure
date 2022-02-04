import os
from urllib.parse import urlparse
from datetime import timedelta

from kombu import Queue


SECRET_KEY = os.environ.get('SECRET_KEY', 'butt')

API_SERVER = 'https://openapi.etsy.com/v2/'
ETSY_SERVER = 'http://etsy.com/'
ETSY_API_KEY = os.environ.get('ETSY_API_KEY')
ETSY_API_SECRET = os.environ.get('ETSY_API_SECRET')

REDIS_CONFIG = urlparse(os.environ.get('REDISCLOUD_URL'))

broker_url = os.environ.get('CLOUDAMQP_URL')
broker_use_ssl = False

# Handle ampqs://
if broker_url.startswith('amqps://'):
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

# These Buried Treasure settings come from the environment, so you know they're
# good for you.

# Score multiplier for user count
BT_USER_WEIGHT = int(os.environ.get('BT_USER_WEIGHT', 100))

# User bonus added if gold is in the materials
BT_GOLD_BONUS = int(os.environ.get('BT_GOLD_BONUS', 50))

# Number of low user count listing ids preserved when scrubbing scrubs
BT_SCRUB_LIMIT = int(os.environ.get('BT_SCRUB_LIMIT', 5000))

# Number of listing records to get at a time
BT_CHUNK_SIZE = int(os.environ.get('BT_CHUNK_SIZE', 50))

# Number of listings to keep data for
BT_LISTING_LIMIT = int(os.environ.get('BT_LISTING_LIMIT', 500))

# The time in days after which age goes from detriment to benefit
BT_AGE_PIVOT = int(os.environ.get('BT_AGE_PIVOT', 1000))
