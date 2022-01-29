"""
Tests for the Buried Treasure Flask app.
"""
import json

from bs4 import BeautifulSoup

from app import app, r


class TestIndex(object):
    """Tests for the index page."""
    def setup_method(self, method):
        app.testing = True
        self.client = app.test_client()

        for i in range(1000):
            r.zadd('treasures', {i: i})
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
                'users': 10,
            }))

    def test_get_response(self):
        """Should return a response."""
        response = self.client.get('/')

        assert response.status_code == 200

    def test_get_has_treasures(self):
        """Should display treasures!"""
        response = self.client.get('/')

        document = BeautifulSoup(response.data)

        for i in range(999, 899, -1):
            assert document.find(id='listing_%s' % i) is not None

    def test_get_100_treasures(self):
        """Should display up to 100 treasures."""
        response = self.client.get('/')

        document = BeautifulSoup(response.data)

        assert len(document.find(id='treasures').find_all('li')) == 100
