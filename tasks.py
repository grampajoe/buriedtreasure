import json
import random
import time

import newrelic.agent
import requests
from celery import Celery
from celery.utils.log import get_task_logger

from app import app, r

celery = Celery(__name__)

celery.config_from_object(app.config)

logger = get_task_logger(__name__)


def api_call(endpoint, **params):
    params['api_key'] = app.config['ETSY_API_KEY']
    url = app.config['API_SERVER'] + endpoint
    response = requests.get(url, params=params)

    # Send rate limit metrics to NewRelic
    rate_limit = response.headers.get('X-RateLimit-Limit')
    rate_limit_remaining = response.headers.get('X-RateLimit-Remaining')
    if rate_limit is not None:
        newrelic.agent.record_custom_metrics([
            ('Custom/Etsy/RateLimit', int(rate_limit)),
            ('Custom/Etsy/RateLimitRemaining', int(rate_limit_remaining)),
        ])

    try:
        return response.json()
    except ValueError:
        app.logger.error('API request failed: %s %s' % (
            response.status_code, response.text,
        ))
        raise


def get_treasuries():
    """Returns recent treasury data with listing data."""
    response = api_call(
        'treasuries',
        sort_on='created',
        fields='user_id,listings',
    )

    return response['results']


def unique_users(treasuries):
    """Returns a map of listing ids to unique user ids."""
    listings = {}

    for treasury in treasuries:
        user_id = str(treasury['user_id'])
        for listing in treasury['listings']:
            listing_id = listing['data']['listing_id']
            listings.setdefault(listing_id, set([])).add(user_id)

    return listings


def get_listing_data(*listing_ids):
    """Returns data for a given listing ID."""
    response = api_call(
        'listings/%s' % ','.join(map(str, listing_ids)),
        fields='listing_id,state,views,quantity,'
               'materials,title,url,price,currency_code,original_creation_tsz',
        includes='Shop(url,shop_name),Images(url_170x135):1:0',
    )

    return response['results']


def purge_data(listing_id):
    """Purges all data for listing listing_id."""
    r.delete('listings.%s.data' % listing_id)
    r.delete('listings.%s.users' % listing_id)
    r.zrem('treasures', listing_id)


def listing_is_active(listing):
    """Returns whether a listing is active."""
    return (
        listing.get('state', '') == 'active' and
        listing.get('quantity', 0) > 0 and
        listing.get('views', 0) > 0
    )


def save_listing(listing):
    """Save a listing."""
    r.set(
        'listings.%s.data' % listing['listing_id'],
        json.dumps(listing),
    )


def score_listing(listing):
    """Calculate and save a listing's score."""
    user_weight = app.config.get('BT_USER_WEIGHT')
    gold_bonus = app.config.get('BT_GOLD_BONUS')
    age_pivot = app.config.get('BT_AGE_PIVOT')

    # Age is expressed in days
    age = (
        time.time() - float(listing['original_creation_tsz'])
    ) / (
        60 * 60 * 24  # One day in seconds
    )

    score = (
        (listing['users'] + (gold_bonus if 'gold' in listing['materials'] else 0))
        * user_weight
        * abs(1 - (age / age_pivot))
    ) / (
        float(listing['views'])
        * float(listing['quantity'])
        + 1
    )

    r.zadd('treasures', listing['listing_id'], score)


@celery.task
def fetch_listings():
    """Fetches and stores listing scores and user ids."""
    treasuries = get_treasuries()
    user_map = unique_users(treasuries)

    users_pipe = r.pipeline()
    score_pipe = r.pipeline()
    for listing_id in user_map.keys():
        users_pipe.smembers('listings.%s.users' % listing_id)
        score_pipe.zscore('treasures', listing_id)

    users_list = users_pipe.execute()
    score_list = score_pipe.execute()

    combined_data = zip(user_map.keys(), users_list, score_list)

    update_pipe = r.pipeline()

    for listing_id, existing_users, score in combined_data:
        users = user_map[listing_id]
        all_users = users.union(existing_users)

        if not score and len(all_users) > 1:
            logger.debug(
                'Found %s users for %s: %r' %
                (len(all_users), listing_id, all_users),
            )

            update_pipe.zadd('treasures', listing_id, 0)

        update_pipe.sadd('listings.%s.users' % listing_id, *users)

    update_pipe.execute()


@celery.task
def scrub_scrubs():
    """Randomly culls single-user lists."""
    scrub_limit = app.config.get('BT_SCRUB_LIMIT')

    users_keys = r.keys('listings.*.users')

    # Preserve at least 5000, scrubbing half the remainder
    scrub_count = max(len(users_keys) - scrub_limit, 0)/2

    for key in random.sample(users_keys, scrub_count):
        if r.scard(key) < 2:
            _, listing_id, _ = key.split('.')
            purge_data(listing_id)


@celery.task
def fetch_detail(*listing_ids):
    """Fetches and stores detailed listing data."""
    data = get_listing_data(*listing_ids)

    for listing in data:
        if listing_is_active(listing):
            listing['users'] = r.scard('listings.%s.users' % listing['listing_id'])
            save_listing(listing)
            score_listing(listing)
        else:
            purge_data(listing['listing_id'])


@celery.task
def process_listings():
    """Process all listings."""
    chunk_size = app.config.get('BT_CHUNK_SIZE', 50)
    listing_limit = app.config.get('BT_LISTING_LIMIT', 500)

    listing_ids = r.zrevrange('treasures', 0, listing_limit - 1)

    for i in xrange(0, len(listing_ids), chunk_size):
        fetch_detail.delay(
            *listing_ids[i: i + chunk_size]
        )

    # Purge the unworthy
    unworthy_ids = r.zrange('treasures', 0, -(listing_limit + 1))

    for listing_id in unworthy_ids:
        purge_data(listing_id)
