from flask import Flask, render_template
import redis
import json

app = Flask(__name__)

app.secret_key = "\x9bT\xc2\xea\x03\xc2\x9b]\xa2\xeb\xcb\xe5\xce[\x19^\xaf3\xbf\xbb\xc4s\xb4'"

app.config.from_object('settings')


def get_redis():
    """Get a Redis connection."""
    return redis.Redis(
        host=app.config['REDIS_CONFIG'].hostname,
        port=app.config['REDIS_CONFIG'].port,
        password=app.config['REDIS_CONFIG'].password,
    )


r = get_redis()


@app.route('/')
def index():
    treasure_ids = r.zrevrange('treasures', 0, 100)
    treasure_keys = map(lambda s: 'listings.'+str(s), treasure_ids)
    treasures = []

    pipe = r.pipeline()
    for treasure_key in treasure_keys:
        pipe.get(treasure_key+'.data')

    treasure_data = [
        json.loads(data) for data in pipe.execute()
        if data is not None
    ]

    pipe = r.pipeline()
    for treasure in treasure_data:
        pipe.smembers('listings.%s.users' % treasure['listing_id'])

    treasure_users = pipe.execute()

    for treasure, users in zip(treasure_data, treasure_users):
        treasure['users'] = users
        treasures.append(treasure)

    return render_template('index.html', treasures=treasures, sort='value')


if __name__ == '__main__':
    app.run(debug=True)
