from celery import Celery
import json
import requests

from app import app, r

celery = Celery('tasks')

celery.config_from_object('celeryconfig')


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
    response = api_call('treasuries', sort_on='created')

    return response['results']


def unique_users(treasuries):
    """Returns a map of listing ids to unique user ids."""
    listings = {}

    for treasury in treasuries:
        user_id = treasury['user_id']
        for listing in treasury['listings']:
            listing_id = listing['data']['listing_id']
            listings.setdefault(listing_id, set([])).add(user_id)

    return listings


@celery.task
def fetch_listings():
    """Fetches and stores listing scores and user ids."""
    treasuries = get_treasuries()
    user_map = unique_users(treasuries)

    for listing_id, users in user_map.iteritems():
        if not r.zscore('treasures', listing_id):
            r.zadd('treasures', listing_id, 0)

        r.sadd('listings.%s.users' % listing_id, *users)


def get_listing_data(listing_id):
    """Returns data for a given listing ID."""
    response = api_call('listings/%s' % listing_id, includes='Shop,Images')

    return response['results'].pop()


@celery.task
def fetch_detail(listing_id):
    """Fetches and stores detailed listing data."""
    data = get_listing_data(listing_id)

    if data.get('state', '') == 'active':
        r.set('listings.%s.data' % listing_id, json.dumps(data))
        return True
    else:
        return False


@celery.task
def score_listing(active, listing_id):
    """Calculate and save a listing's score."""
    if not active:
        r.zrem('treasures', listing_id)
        r.delete('listings.%s.users' % listing_id)
        r.delete('listings.%s.data' % listing_id)
    else:
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
    for listing_id in r.zrevrange('treasures', 0, 999):
        fetch_detail.apply_async(
            [listing_id],
            link=score_listing.s(listing_id),
        )

    # Purge the unworthy
    r.zremrangebyrank('treasures', 0, -1001)
