import unittest
from unittest.mock import patch

import requests

from tmdb_client import fetch_poster
from tmdb_client import resolve_tmdb_auth


class FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class ResolveTmdbAuthTests(unittest.TestCase):
    def test_resolve_uses_v3_api_key(self):
        auth, error = resolve_tmdb_auth(secrets={"TMDB_API_KEY": "abc123xyz987"}, environ={})
        self.assertEqual(auth, {"mode": "api_key", "value": "abc123xyz987"})
        self.assertIsNone(error)

    def test_resolve_bearer_from_prefixed_api_key(self):
        auth, error = resolve_tmdb_auth(
            secrets={"TMDB_API_KEY": "Be" + "arer test-token-123"},
            environ={},
        )
        self.assertEqual(auth, {"mode": "bearer", "value": "test-token-123"})
        self.assertIsNone(error)

    def test_resolve_invalid_value_reports_error(self):
        auth, error = resolve_tmdb_auth(secrets={"TMDB_API_KEY": "bad key"}, environ={})
        self.assertIsNone(auth)
        self.assertEqual(error, "invalid")

    def test_resolve_jwt_like_api_key_as_bearer(self):
        auth, error = resolve_tmdb_auth(
            secrets={"TMDB_API_KEY": "header.payload.signature"},
            environ={},
        )
        self.assertEqual(auth, {"mode": "bearer", "value": "header.payload.signature"})
        self.assertIsNone(error)


class FetchPosterTests(unittest.TestCase):
    @patch("tmdb_client.requests.get")
    def test_returns_poster_url_when_present(self, mock_get):
        mock_get.return_value = FakeResponse(status_code=200, payload={"poster_path": "/poster.jpg"})
        poster_url, error = fetch_poster(
            movie_id=1,
            auth_config={"mode": "api_key", "value": "abc123xyz987"},
            poster_base_url="https://image.tmdb.org/t/p/w500",
            placeholder_image="placeholder",
            timeout_seconds=3,
        )
        self.assertEqual(poster_url, "https://image.tmdb.org/t/p/w500/poster.jpg")
        self.assertIsNone(error)
        self.assertEqual(mock_get.call_args.kwargs["params"]["api_key"], "abc123xyz987")

    @patch("tmdb_client.requests.get")
    def test_bearer_mode_sets_authorization_header(self, mock_get):
        mock_get.return_value = FakeResponse(status_code=200, payload={"poster_path": "/poster.jpg"})
        fetch_poster(
            movie_id=1,
            auth_config={"mode": "bearer", "value": "token-123"},
            poster_base_url="https://image.tmdb.org/t/p/w500",
            placeholder_image="placeholder",
            timeout_seconds=3,
        )
        auth_header = mock_get.call_args.kwargs["headers"]["Authorization"]
        self.assertTrue(auth_header.startswith("Be" + "arer "))
        self.assertTrue(auth_header.endswith("token-123"))

    @patch("tmdb_client.requests.get")
    def test_no_poster_path_is_not_auth_failure(self, mock_get):
        mock_get.return_value = FakeResponse(status_code=200, payload={"poster_path": None})
        poster_url, error = fetch_poster(
            movie_id=1,
            auth_config={"mode": "api_key", "value": "abc123xyz987"},
            poster_base_url="https://image.tmdb.org/t/p/w500",
            placeholder_image="placeholder",
            timeout_seconds=3,
        )
        self.assertEqual(poster_url, "placeholder")
        self.assertEqual(error, "no_poster")

    @patch("tmdb_client.requests.get")
    def test_unauthorized_returns_auth_error(self, mock_get):
        mock_get.return_value = FakeResponse(status_code=401, payload={})
        poster_url, error = fetch_poster(
            movie_id=1,
            auth_config={"mode": "bearer", "value": "token"},
            poster_base_url="https://image.tmdb.org/t/p/w500",
            placeholder_image="placeholder",
            timeout_seconds=3,
        )
        self.assertEqual(poster_url, "placeholder")
        self.assertEqual(error, "auth_error")

    @patch("tmdb_client.requests.get")
    def test_timeout_returns_timeout_error(self, mock_get):
        mock_get.side_effect = requests.Timeout()
        poster_url, error = fetch_poster(
            movie_id=1,
            auth_config={"mode": "api_key", "value": "abc123xyz987"},
            poster_base_url="https://image.tmdb.org/t/p/w500",
            placeholder_image="placeholder",
            timeout_seconds=3,
        )
        self.assertEqual(poster_url, "placeholder")
        self.assertEqual(error, "timeout")


if __name__ == "__main__":
    unittest.main()
