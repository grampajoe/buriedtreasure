import json
from mock import patch

from app import r

from tasks import (
    get_treasuries,
    unique_users,
    fetch_listings,
    get_listing_data,
    fetch_detail,
    score_listing,
    process_listings,
)


def fake_treasuries():
    listings = [
        {
            'data': {
                'listing_id': '1',
            },
        },
        {
            'data': {
                'listing_id': '2',
            },
        },
    ]

    treasuries = [
        {
            'user_id': '1',
            'listings': [
                listings[0],
            ],
        },
        {
            'user_id': '1',
            'listings': [
                listings[0],
                listings[1],
            ],
        },
        {
            'user_id': '2',
            'listings': [
                listings[1],
            ],
        },
    ]

    return treasuries


@patch('tasks.api_call')
def test_get_treasuries(api_call):
    """Should get a list of treasuries with listing data."""
    api_call.return_value = {
        'results': [
            {
                'user_id': i,
                'listings': [
                    {
                        'data': {
                            'listing_id': j,
                        },
                    }
                    for j in range(10)
                ],
            }
            for i in range(10)
        ],
    }

    result = get_treasuries()

    api_call.assert_called_with(
        'treasuries',
        sort_on='created',
    )
    assert result == api_call.return_value['results']


def test_unique_users():
    """Should return a map of listing ids to unique user ids."""
    listing_map = unique_users(fake_treasuries())

    assert listing_map['1'] == set(['1'])
    assert listing_map['2'] == set(['1', '2'])


class TestFetchListings(object):
    """Tests for the fetch_listings task."""
    def setup_method(self, method):
        self.get_treasuries_patch = patch('tasks.get_treasuries')
        self.get_treasuries = self.get_treasuries_patch.start()
        self.get_treasuries.return_value = fake_treasuries()

        r.flushdb()

    def teardown_method(self, method):
        self.get_treasuries_patch.stop()

        r.flushdb()

    def test_fetch_listings(self):
        """Should fetch and store listing scores and user ids."""
        fetch_listings()

        assert r.zscore('treasures', 1) == 0
        assert r.smembers('listings.1.users') == set(['1'])

        assert r.zscore('treasures', 2) == 0
        assert r.smembers('listings.2.users') == set(['1', '2'])

    def test_fetch_listings_existing_score(self):
        """Should not overwrite existing scores."""
        r.zadd('treasures', '1', 9000)

        fetch_listings()

        assert r.zscore('treasures', '1') == 9000

    def test_fetch_listings_existing_users(self):
        """Should add to existing sets of users."""
        r.sadd('listings.1.users', '9', '10', 'three')

        fetch_listings()

        assert r.smembers('listings.1.users') == set(['9', '10', 'three', '1'])


@patch('tasks.api_call')
def test_get_listing_data(api_call):
    """Should get listing data given a listing ID."""
    listing_id = '123'
    listing = {
        'materials': ['poop', 'butt'],
    }

    api_call.return_value = {
        'results': [listing],
    }

    data = get_listing_data(listing_id)

    assert data == listing
    api_call.assert_called_with(
        'listings/%s' % listing_id,
        includes='Shop,Images',
    )


class TestFetchDetail(object):
    """Tests for the fetch_detail task."""
    def setup_method(self, method):
        self.get_listing_data_patch = patch('tasks.get_listing_data')
        self.get_listing_data = self.get_listing_data_patch.start()

        self.get_listing_data.return_value = self.listing = {
            'materials': ['poop', 'butt']
        }

    def teardown_method(self, method):
        self.get_listing_data_patch.stop()

        r.flushdb()

    def test_fetch_detail(self):
        """Should get and store listing data."""
        listing_id = '123'

        fetch_detail(listing_id)

        data = json.loads(r.get('listings.%s.data' % listing_id))

        assert data == self.listing


def assert_almost_equal(actual, expected, error=0.01):
    """Asserts that expected is within diff of actual."""
    diff = abs(expected - actual)
    actual_error = float(diff) / expected

    assert actual_error < error, '%s was not within %d%% of %s.' % (
        actual, error * 100, expected,
    )


class TestScoreListing(object):
    """Tests for listing scoring."""
    def setup_method(self, method):
        r.flushdb()

    def teardown_method(self, method):
        r.flushdb()

    def test_score(self):
        """Should score things based on a cool formula."""
        # 4 users, 9000 views, no gold
        r.sadd('listings.1.users', 1, 2, 3, 4)
        r.set('listings.1.data', json.dumps({
            'quantity': 1,
            'state': 'active',
            'views': 9000,
            'materials': [],
        }))

        # 40 users, 9 views, 10 quantity, no gold
        r.sadd('listings.2.users', *range(40))
        r.set('listings.2.data', json.dumps({
            'quantity': 10,
            'state': 'active',
            'views': 9,
            'materials': [],
        }))

        # 1 user, 10 views, 10 quantity, gold
        r.sadd('listings.3.users', 1)
        r.set('listings.3.data', json.dumps({
            'quantity': 10,
            'state': 'active',
            'views': 10,
            'materials': ['gold'],
        }))

        score_listing(1)
        score_listing(2)
        score_listing(3)

        assert_almost_equal(r.zscore('treasures', '1'), 0.004443950672147539)
        assert_almost_equal(r.zscore('treasures', '2'), 4.395604395604396)
        assert_almost_equal(r.zscore('treasures', '3'), 9.900990099009901)


class TestProcessListings(object):
    """Tests for the process_listings task."""
    def setup_method(self, method):
        r.flushdb()

    def teardown_method(self, method):
        r.flushdb()

    @patch('tasks.score_listing')
    @patch('tasks.fetch_detail')
    def test_processes_listings(self, fetch_detail, score_listing):
        """Should call fetch_detail and score_listing on all listings."""
        for i in range(2000):
            r.zadd('treasures', i, i)

        process_listings()

        assert fetch_detail.apply_async.call_count == 1000
        fetch_detail.apply_async.assert_called_with(
            ['999'], link=score_listing.s.return_value,
        )
        score_listing.s.assert_called_with('999')

        assert r.zcard('treasures') == 1000
