from celery import Celery
import json
import requests
import redis

from app import app, get_redis

celery = Celery('tasks')

celery.config_from_object('celeryconfig')


r = get_redis(db=1)


def api_call(endpoint, **params):
    params['api_key'] = app.config['ETSY_API_KEY']
    url = app.config['API_SERVER'] + endpoint
    response = requests.get(url, params=params)

    return response.json()

@celery.task
def fetch_treasuries():
    data =  api_call('treasuries', sort_on='created') 
    listings = {}

    for treasury in data['results']:
        for listing in treasury['listings']:
            listing_id = listing['data']['listing_id']
            if listing_id in listings:
                listings[listing_id]['users'].add(int(treasury['user_id']))
                print 'FOUND '+str(len(listings[listing_id]['users']))
            else:
                listings[listing['data']['listing_id']] = {
                            'data': json.dumps(listing['data']),
                            'users': set([int(treasury['user_id'])]),
                        }

    for listing_id in listings:
        listing_key = 'listings.'+str(listing_id)

        users = set(map(int, r.smembers(listing_key+'.users')))
        new_users = listings[listing_id]['users'] - users
        all_users = users | listings[listing_id]['users'] 

        # Only score a listing if it has more than one user and a new
        # user was found.
        if len(all_users) > 1 and len(new_users):
            # Schedule a scrape so the rate limit isn't hit
            add_treasure.delay(listing_id, all_users)

        # Keep track of users for all listings
        for user_id in listings[listing_id]['users']:
            r.sadd(listing_key+'.users', user_id)

    return len(listings)

@celery.task
def add_treasure(listing_id, users):
    listing_key = 'listings.'+str(listing_id)
    data = listing_detail(listing_id)
    if data is not None:
        score = score_listing(users, data)
        r.zadd('treasures', listing_id, score)
        r.set(listing_key+'.data', json.dumps(data))

def listing_detail(listing_id):
    """Get detailed listing info."""
    data = api_call('listings/'+str(listing_id), includes='Shop,Images')
    if 'results' in data and len(data['results']):
        return data['results'].pop()
    else:
        return None

def score_listing(users, data):
    """Score a listing."""
    if data['quantity'] > 0 and data['state'] == 'active':
        score = (len(users)*10)/(float(data['views'])*float(data['quantity'])+1)
        if 'gold' in data['materials'] or 'gold' in data['title'].lower():
            score *= 100

        return score
    else:
        return None

def rescore():
    """Recompute scores."""
    treasure_count = r.zcard('treasures')
    treasures = r.zrange('treasures', 0, treasure_count)

    for treasure_id in treasures:
        users = set(map(int, r.smembers('listings.'+str(treasure_id)+'.users')))
        data = json.loads(r.get('listings.'+str(treasure_id)+'.data'))

        score = score_listing(users, data)

        if score is not None:
            r.zadd('treasures', treasure_id, score)
        else:
            r.zrem('treasures', treasure_id)
