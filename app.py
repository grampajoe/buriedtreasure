from flask import Flask, render_template
import redis
import json

app = Flask(__name__)

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
    treasure_ids = r.zrevrange('treasures', 0, 99)
    treasure_keys = map(lambda s: 'listings.'+str(s), treasure_ids)

    pipe = r.pipeline()
    for treasure_key in treasure_keys:
        pipe.get(treasure_key+'.data')

    treasures = [
        json.loads(data) for data in pipe.execute()
        if data is not None
    ]

    return render_template('index.html', treasures=treasures, sort='value')


if __name__ == '__main__':
    app.run(debug=True)
