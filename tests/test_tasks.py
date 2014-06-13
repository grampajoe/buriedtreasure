import json
from mock import patch, call

from app import r

from tasks import (
    get_treasuries,
    unique_users,
    fetch_listings,
    get_listing_data,
    fetch_detail,
    score_listing,
    process_listings,
    purge_old_data,
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
    listing_ids = [1, 2, 3]
    listings = [
        {'listing_id': '1', 'materials': ['poop', 'butt']},
        {'listing_id': '2', 'materials': ['poop', 'butt']},
        {'listing_id': '3', 'materials': ['poop', 'butt']},
    ]

    api_call.return_value = {
        'results': listings,
    }

    data = get_listing_data(*listing_ids)

    assert data == listings
    api_call.assert_called_with(
        'listings/%s' % ','.join(map(str, listing_ids)),
        includes='Shop,Images',
    )


class TestFetchDetail(object):
    """Tests for the fetch_detail task."""
    def setup_method(self, method):
        self.get_listing_data_patch = patch('tasks.get_listing_data')
        self.get_listing_data = self.get_listing_data_patch.start()

        self.listings = [
            {
                'listing_id': '1',
                'state': 'active',
                'quantity': 1,
                'views': 1,
                'materials': ['poop', 'butt'],
            },
            {
                'listing_id': '2',
                'state': 'active',
                'quantity': 1,
                'views': 1,
                'materials': ['poop', 'butt'],
            },
            {
                'listing_id': '3',
                'state': 'active',
                'quantity': 1,
                'views': 1,
                'materials': ['poop', 'butt'],
            },
        ]

        self.get_listing_data.return_value = self.listings

    def teardown_method(self, method):
        self.get_listing_data_patch.stop()

        r.flushdb()

    @patch('tasks.score_listing')
    def test_fetch_detail(self, score_listing):
        """Should get and store listing data."""
        listing_ids = ['1', '2', '3']

        result = fetch_detail(*listing_ids)

        for listing_id, listing in zip(listing_ids, self.listings):
            data = json.loads(r.get('listings.%s.data' % listing_id))

            assert data == listing
            score_listing.assert_any_call(listing_id)


def assert_does_not_exist(listing_id):
    """Asserts that listing data does not exist for listing_id."""
    assert not r.exists('listings.%s.data' % listing_id)
    assert not r.exists('listings.%s.users' % listing_id)
    assert r.zrank('treasures', listing_id) is None


def store_fake_data(listing_id):
    """Stores fake listing data for listing_id."""
    r.set('listings.%s.data' % listing_id, '{"hello": "there"}')
    r.sadd('listings.%s.users' % listing_id, '999')
    r.zadd('treasures', listing_id, 9000)


class TestFetchDetailDestruction(object):
    """Tests for destroying bad data!!!"""
    def setup_method(self, method):
        r.flushdb()

        self.get_listing_data_patch = patch('tasks.get_listing_data')
        self.get_listing_data = self.get_listing_data_patch.start()

    def teardown_method(self, method):
        self.get_listing_data_patch.stop()
        r.flushdb()

    @patch('tasks.score_listing')
    def test_dont_store_inactive(self, score_listing):
        """Should not store data for inactive listings."""
        self.get_listing_data.return_value = [
            {
                'listing_id': '1',
                'materials': ['fart'],
                'state': 'butt',
                'quantity': 1,
                'views': 1,
            },
        ]

        fetch_detail('1')

        assert_does_not_exist('1')
        assert score_listing.called == False

    @patch('tasks.score_listing')
    def test_dont_store_empty(self, score_listing):
        """Should not store data for empty listings."""
        self.get_listing_data.return_value = [
            {
                'listing_id': '2',
                'materials': ['fart'],
                'state': 'active',
                'quantity': 0,
                'views': 1,
            },
        ]

        fetch_detail('2')

        assert_does_not_exist('2')
        assert score_listing.called == False

    @patch('tasks.score_listing')
    def test_dont_store_unviewed(self, score_listing):
        """Should not store data for unviewed listings."""
        self.get_listing_data.return_value = [
            {
                'listing_id': '3',
                'materials': ['fart'],
                'state': 'active',
                'quantity': 1,
                'views': 0,
            },
        ]

        fetch_detail('3')

        assert_does_not_exist('3')
        assert score_listing.called == False

    def test_destroy_inactive(self):
        """Should delete everything about an inactive listing."""
        self.get_listing_data.return_value = [
            {
                'listing_id': '1',
                'materials': ['fart'],
                'state': 'butt',
                'quantity': 1,
                'views': 1,
            },
        ]

        store_fake_data('1')

        fetch_detail('1')

        assert_does_not_exist('1')

    def test_destroy_empty(self):
        """Should delete everything about an empty listing."""
        self.get_listing_data.return_value = [
            {
                'listing_id': '2',
                'materials': ['fart'],
                'state': 'active',
                'quantity': 0,
                'views': 1,
            },
        ]

        store_fake_data('2')

        fetch_detail('2')

        assert_does_not_exist('2')

    def test_destroy_unviewed(self):
        """Should delete everything about an unviewed listing."""
        self.get_listing_data.return_value = [
            {
                'listing_id': '3',
                'materials': ['fart'],
                'state': 'active',
                'quantity': 1,
                'views': 0,
            },
        ]

        store_fake_data('3')

        fetch_detail('3')

        assert_does_not_exist('3')


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

        assert fetch_detail.delay.call_count == 10

        for mock_call in fetch_detail.delay.mock_calls:
            _, args, _ = mock_call
            assert len(args) == 50

        assert r.zcard('treasures') == 500


class TestPurgeOldData(object):
    """Tests for the purge_old_data task."""
    def test_purges_old_data(self):
        """Should delete data for listings that no longer have a score."""
        store_fake_data('123')
        r.zrem('treasures', '123')

        purge_old_data()

        assert_does_not_exist('123')
