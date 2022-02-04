import os
from urllib.parse import urlparse


SECRET_KEY = os.environ.get('SECRET_KEY', 'butt')

API_SERVER = 'https://openapi.etsy.com/v2/'
ETSY_SERVER = 'http://etsy.com/'
ETSY_API_KEY = os.environ.get('ETSY_API_KEY')
ETSY_API_SECRET = os.environ.get('ETSY_API_SECRET')

REDIS_CONFIG = urlparse(os.environ.get('REDISCLOUD_URL'))

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
