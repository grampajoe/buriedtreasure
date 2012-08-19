import unittest
import app
import mock

class MockAPIResponse(object):
    def __init__(self, data, status_code=200):
        self.data = data
        self.status_code = status_code

class EtsyTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.app.test_client()

    def tearDown(self):
        pass

    def test_oauth_success(self):
        mock_oauth_response = {
                'oauth_token': 'test',
                'oauth_token_secret': 'test',
                'user_id': 1,
            }
        mock_user_response = MockAPIResponse({
                'results': [{
                    'login_name': 'Test User',
                }],
            })

        with mock.patch('app.etsy.handle_oauth1_response',
                return_value=mock_oauth_response):
            with mock.patch('app.etsy.get', return_value=mock_user_response):
                response = self.app.get('/authorized/?oauth_verifier=1',
                        follow_redirects=True)

                self.assertEqual(response.status_code, 200)
                self.assertIn('You are now logged in.', response.data)

    def test_oauth_denied(self):
        with mock.patch('app.etsy.handle_oauth1_response',
                return_value=None):
            response = self.app.get('/authorized/?oauth_verifier=1',
                    follow_redirects=True)

            self.assertEqual(response.status_code, 200)
            self.assertIn('Access not granted.', response.data)
