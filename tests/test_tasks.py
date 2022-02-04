import json
import time
from unittest.mock import patch, call, Mock

from app import r

from tasks import (
    get_treasuries,
    unique_users,
    fetch_listings,
    get_listing_data,
    fetch_detail,
    score_listing,
    process_listings,
    scrub_scrubs,
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
            'user_id': 1,
            'listings': [
                listings[0],
            ],
        },
        {
            'user_id': 1,
            'listings': [
                listings[0],
                listings[1],
            ],
        },
        {
            'user_id': 2,
            'listings': [
                listings[1],
            ],
        },
    ]

    return treasuries


def listings():
    """Some fake listings!"""
    return [
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


def assert_does_not_exist(listing_id):
    """Asserts that listing data does not exist for listing_id."""
    assert not r.exists('listings.%s.data' % listing_id)
    assert not r.exists('listings.%s.users' % listing_id)
    assert r.zrank('treasures', listing_id) is None


def store_fake_data(listing_id, score=9000):
    """Stores fake listing data for listing_id."""
    r.set('listings.%s.data' % listing_id, '{"hello": "there"}')
    r.sadd('listings.%s.users' % listing_id, '999')
    r.zadd('treasures', {listing_id: score})


@patch('tasks.process_listings')
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

    @patch('tasks.api_call')
    def test_get_treasuries(self, api_call, process_listings):
        """Should get a list of treasuries with listing data."""
        api_call.return_value = {
            'results': [
                {
                    'user_id': str(i),
                    'listings': [
                        {
                            'data': {
                                'listing_id': str(j),
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
            fields='user_id,listings',
        )
        assert result == api_call.return_value['results']

    def test_fetch_listings_single_user(self, process_listings):
        """Should store user IDs but not fetch items with one user."""
        fetch_listings()

        assert r.smembers('listings.1.users') == set([b'1'])
        assert '1' not in process_listings.call_args[0]

    def test_fetch_listings_multiple_users(self, process_listings):
        """Should store user IDs and fetch items with more than one user."""
        fetch_listings()

        assert r.smembers('listings.2.users') == set([b'1', b'2'])
        assert '2' in process_listings.call_args[0]

    def test_fetch_listings_single_new_user(self, process_listings):
        """Should fetch existing items with a single new user."""
        r.sadd('listings.1.users', '9')

        fetch_listings()

        assert r.smembers('listings.1.users') == set([b'1', b'9'])
        assert '1' in process_listings.call_args[0]

    def test_fetch_listings_existing_users(self, process_listings):
        """Should add to existing sets of users."""
        r.sadd('listings.1.users', '9', '10', 'three')

        fetch_listings()

        assert r.smembers('listings.1.users') == set([b'9', b'10', b'three', b'1'])

    def test_fetch_listings_duplicate_user_no_fetch(self, process_listings):
        """Should not fetch the listing if only one unique user ID is found."""
        r.sadd('listings.1.users', '1')

        fetch_listings()

        assert r.smembers('listings.1.users') == set([b'1'])
        assert '1' not in process_listings.call_args[0]


class TestScrubScrubs():
    """Tests for the scrub_scrubs task."""
    def teardown_method(self, method):
        r.flushdb()

    def test_scrub_scrubs(self):
        """Should randomly cull user lists of one user."""
        for i in range(50):
            r.sadd('listings.%s.users' % i, '1', '2')

        for i in range(50, 6000):
            r.sadd('listings.%s.users' % i, '1')

        scrub_scrubs()

        # All of the 2 or more lists should be there
        for i in range(50):
            assert r.scard('listings.%s.users' % i) == 2

        # Should leave at least 5000, taking about half of the remainder
        remaining_keys = r.keys('listings.*.users')
        assert len(remaining_keys) <= 5550
        assert len(remaining_keys) >= 5000


@patch('tasks.get_listing_data', new=Mock(return_value=listings()))
class TestFetchDetail(object):
    """Tests for the fetch_detail task."""
    def setup_method(self, method):
        self.listing_ids = [listing['listing_id'] for listing in listings()]

        for listing_id in self.listing_ids:
            r.sadd('listings.%s.users' % listing_id, 1, 2, 3)

    def teardown_method(self, method):
        r.flushdb()

    @patch('tasks.api_call')
    def test_get_listing_data(self, api_call):
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
            fields='listing_id,state,views,quantity,'
                   'materials,title,url,price,currency_code,original_creation_tsz',
            includes='Shop(url,shop_name),Images(url_170x135):1:0',
        )

    @patch('tasks.score_listing')
    def test_fetch_detail(self, score_listing):
        """Should get and store listing data."""
        result = fetch_detail(*self.listing_ids)

        for listing in listings():
            data = json.loads(r.get('listings.%s.data' % listing['listing_id']))

            assert data.pop('users') == 3
            assert data == listing

    @patch('tasks.score_listing')
    def test_scores_things(self, score_listing):
        """Should score each fetched listing."""
        fetch_detail(*self.listing_ids)

        for listing in listings():
            listing['users'] = 3
            score_listing.assert_any_call(listing)


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

        fetch_detail.apply('1')

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

        fetch_detail.apply('2')

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

        fetch_detail.apply('3')

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

        fetch_detail.apply('1')

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

        fetch_detail.apply('2')

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

        fetch_detail.apply('3')

        assert_does_not_exist('3')


class TestScoreListing(object):
    """Tests for listing scoring."""
    def teardown_method(self, method):
        r.flushdb()

    def test_score(self):
        """Should score things based on a cool formula."""
        now = str(time.time())

        # 4 users, 9000 views, no gold
        listing1 = {
            'listing_id': 1,
            'quantity': 1,
            'state': 'active',
            'views': 9000,
            'materials': [],
            'users': 4,
            'original_creation_tsz': now,
        }

        # 40 users, 9 views, 10 quantity, no gold
        listing2 = {
            'listing_id': 2,
            'quantity': 10,
            'state': 'active',
            'views': 9,
            'materials': [],
            'users': 40,
            'original_creation_tsz': now,
        }

        # 1 user, 10 views, 10 quantity, gold
        listing3 = {
            'listing_id': 3,
            'quantity': 10,
            'state': 'active',
            'views': 10,
            'materials': ['gold'],
            'users': 1,
            'original_creation_tsz': now,
        }

        score_listing(listing1)
        score_listing(listing2)
        score_listing(listing3)

        assert r.zscore('treasures', '1') < r.zscore('treasures', '2')
        assert r.zscore('treasures', '2') < r.zscore('treasures', '3')

    def test_score_decays_with_age(self):
        """Should score older things lower."""
        now = time.time()

        listing1 = {
            'listing_id': 1,
            'quantity': 1,
            'state': 'active',
            'views': 9000,
            'materials': [],
            'users': 4,
            'original_creation_tsz': str(now),
        }

        listing2 = {
            'listing_id': 2,
            'quantity': 1,
            'state': 'active',
            'views': 9000,
            'materials': [],
            'users': 4,
            'original_creation_tsz': str(now - 100),
        }

        listing3 = {
            'listing_id': 3,
            'quantity': 1,
            'state': 'active',
            'views': 9000,
            'materials': [],
            'users': 4,
            'original_creation_tsz': str(now - 500),
        }

        score_listing(listing1) 
        score_listing(listing2)
        score_listing(listing3)

        assert r.zscore('treasures', '1') > r.zscore('treasures', '2')
        assert r.zscore('treasures', '2') > r.zscore('treasures', '3')

    def test_never_negative(self):
        """Event the oldest things shouldn't have negative scores."""
        score_listing({
            'listing_id': 1,
            'quantity': 1,
            'state': 'active',
            'views': 9000,
            'materials': [],
            'users': 4,
            'original_creation_tsz': '1',
        })

        assert r.zscore('treasures', '1') > 0


class TestProcessListings(object):
    """Tests for the process_listings method."""
    def setup_method(self, method):
        self.fetch_detail_patch = patch('tasks.fetch_detail')
        self.fetch_detail = self.fetch_detail_patch.start()

        r.flushdb()

    def teardown_method(self, method):
        self.fetch_detail_patch.stop()

        r.flushdb()

    def test_processes_listings(self):
        """Should call fetch_detail and score_listing on all listings."""
        process_listings(*range(500))

        assert self.fetch_detail.delay.call_count == 10  # chunks of 50

        for mock_call in self.fetch_detail.delay.mock_calls:
            _, args, _ = mock_call
            assert len(args) == 50
