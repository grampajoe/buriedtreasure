from flask import Flask
from flask import render_template, session, url_for, redirect
from flask import flash
from flask.ext.oauth import OAuth
import redis
import json

from code import interact

app = Flask(__name__)

app.secret_key = "\x9bT\xc2\xea\x03\xc2\x9b]\xa2\xeb\xcb\xe5\xce[\x19^\xaf3\xbf\xbb\xc4s\xb4'"

app.config.from_object('settings')

oauth = OAuth()

etsy = oauth.remote_app('etsy',
    base_url=app.config['API_SERVER'],
    request_token_url=app.config['API_SERVER']+'oauth/request_token',
    access_token_url=app.config['API_SERVER']+'oauth/access_token',
    authorize_url=app.config['ETSY_SERVER']+'oauth/signin',
    consumer_key=app.config['ETSY_API_KEY'],
    consumer_secret=app.config['ETSY_API_SECRET'],
    request_token_params = {
        'scope': 'profile_r',
        'oauth_consumer_key': app.config['ETSY_API_KEY'],
    },
)

def get_redis(db=0):
    """Get a Redis connection."""
    return redis.Redis(
        host=app.config['REDIS_CONFIG'].hostname,
        port=app.config['REDIS_CONFIG'].port,
        password=app.config['REDIS_CONFIG'].password,
    )

r = get_redis(db=1)

@app.route('/')
def index():
    treasure_ids = r.zrevrange('treasures', 0, 100)
    treasure_keys = map(lambda s: 'listings.'+str(s), treasure_ids)
    treasures = []
    for treasure_key in treasure_keys:
        data = r.get(treasure_key+'.data')
        if data is not None:
            treasure = json.loads(data)
            treasure['users'] = r.smembers(treasure_key+'.users')
            treasures.append(treasure)
    return render_template('index.html', treasures=treasures, sort='value')

@app.route('/login/')
def login():
    callback_url = url_for('oauth_authorized', _external=True)
    return etsy.authorize(callback=callback_url)

@app.route('/authorized/')
@etsy.authorized_handler
def oauth_authorized(response):
    if response is None:
        flash('Access not granted.', 'error')
        return redirect(url_for('index'))

    session['etsy_token'] = (
        response['oauth_token'],
        response['oauth_token_secret']
    )
    user_response = etsy.get('users/__SELF__/')

    if 'results' in user_response.data and len(user_response.data['results']):
        session['user'] = user_response.data['results'].pop()

        flash('You are now logged in.', 'success')
    else:
        flash('Couldn\'t find user!', 'error')
        session.pop('etsy_token')

    return redirect(url_for('index'))

@app.route('/logout/')
def logout():
    if 'etsy_token' in session:
        session.pop('etsy_token')

    if 'user' in session:
        session.pop('user')

    flash('You are now logged out.', 'info')
    return redirect(url_for('index'))

@etsy.tokengetter
def get_etsy_token():
    return session.get('etsy_token')

if __name__ == '__main__':
    app.run(debug=True)
