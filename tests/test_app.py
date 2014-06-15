"""
Tests for the Buried Treasure Flask app.
"""
import json

from app import app, r


class TestIndex(object):
    """Tests for the index page."""
    def setup_method(self, method):
        app.testing = True
        self.client = app.test_client()

    def test_get_response(self):
        """Should return a response."""
        response = self.client.get('/')

        assert response.status_code == 200

    def test_get_has_treasures(self):
        """Should display treasures!"""
        for i in range(1000):
            r.zadd('treasures', i, i)
            r.sadd('listings.%s.users', str(i))
            r.set('listings.%s.data' % i, json.dumps({
                'listing_id': i,
                'quantity': i,
                'materials': [],
                'views': i,
                'url': 'http://google.com',
                'title': 'HEllo',
                'Images': [
                    {'url_170x135': 'http://google.com'},
                ],
                'price': 123,
                'currency_code': 'USD',
                'Shop': {'shop_name': 'Heollo', 'url': 'http://google.com'},
            }))

        response = self.client.get('/')

        # Really dumb way to say 100 listings should be on the page
        for i in range(1, 101):
            assert 'data-value="%s"' % i in response.data
