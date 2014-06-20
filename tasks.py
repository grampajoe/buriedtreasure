import json
import random

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
    users_keys = r.keys('listings.*.users')

    # Preserve at least 5000, scrubbing half the remainder
    scrub_count = max(len(users_keys) - 5000, 0)/2

    for key in random.sample(users_keys, scrub_count):
        if r.scard(key) < 2:
            _, listing_id, _ = key.split('.')
            purge_data(listing_id)


def get_listing_data(*listing_ids):
    """Returns data for a given listing ID."""
    response = api_call(
        'listings/%s' % ','.join(map(str, listing_ids)),
        fields='listing_id,state,views,quantity,'
               'materials,title,url,price,currency_code',
        includes='Shop(url,shop_name),Images(url_170x135):1:0',
    )

    return response['results']


def purge_data(listing_id):
    """Purges all data for listing listing_id."""
    r.delete('listings.%s.data' % listing_id)
    r.delete('listings.%s.users' % listing_id)
    r.zrem('treasures', listing_id)


@celery.task
def fetch_detail(*listing_ids):
    """Fetches and stores detailed listing data."""
    data = get_listing_data(*listing_ids)

    for listing in data:
        if (
            listing.get('state', '') == 'active' and
            listing.get('quantity', 0) > 0 and
            listing.get('views', 0) > 0
        ):
            listing['users'] = r.scard('listings.%s.users' % listing['listing_id'])
            r.set(
                'listings.%s.data' % listing['listing_id'],
                json.dumps(listing),
            )

            score_listing(listing['listing_id'])
        else:
            purge_data(listing['listing_id'])


def score_listing(listing_id):
    """Calculate and save a listing's score."""
    listing = json.loads(r.get('listings.%s.data' % listing_id))
    users = r.scard('listings.%s.users' % listing_id)

    score = (
        users * 10
    ) / (
        float(listing['views']) * float(listing['quantity']) + 1
    )

    if 'gold' in listing['materials']:
        score = score * 100

    r.zadd('treasures', listing_id, score)


@celery.task
def process_listings():
    """Process all listings."""
    chunk_size = 50
    listing_ids = r.zrevrange('treasures', 0, 499)

    for i in xrange(0, len(listing_ids), chunk_size):
        fetch_detail.delay(
            *listing_ids[i: i + chunk_size]
        )

    # Purge the unworthy
    unworthy_ids = r.zrange('treasures', 0, -501)

    for listing_id in unworthy_ids:
        purge_data(listing_id)
