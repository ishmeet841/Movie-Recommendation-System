import os
from typing import Any, Dict, Mapping, Optional, Tuple

import requests

TMDB_MOVIE_DETAILS_URL = "https://api.themoviedb.org/3/movie/{movie_id}"
TMDB_BEARER_KEYS = ("TMDB_BEARER_TOKEN", "TMDB_V4_ACCESS_TOKEN")
TMDB_API_KEY_KEYS = ("TMDB_API_KEY",)
TMDB_ALL_KEY_NAMES = TMDB_BEARER_KEYS + TMDB_API_KEY_KEYS


def _normalize_value(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _looks_like_jwt(token: str) -> bool:
    parts = token.split(".")
    return len(parts) == 3 and all(parts)


def parse_tmdb_credential(raw_value: Any, key_name: str) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
    normalized = _normalize_value(raw_value)
    if not normalized:
        return None, None

    lower_value = normalized.lower()
    if lower_value.startswith("bearer "):
        token = normalized[7:].strip()
        return ({"mode": "bearer", "value": token}, None) if token and " " not in token else (None, "invalid")

    if key_name in TMDB_BEARER_KEYS:
        return ({"mode": "bearer", "value": normalized}, None) if " " not in normalized else (None, "invalid")

    if key_name in TMDB_API_KEY_KEYS and _looks_like_jwt(normalized):
        return {"mode": "bearer", "value": normalized}, None

    return ({"mode": "api_key", "value": normalized}, None) if " " not in normalized else (None, "invalid")


def _read_mapping_value(mapping: Any, key: str) -> Any:
    try:
        return mapping.get(key)
    except Exception:
        return None


def resolve_tmdb_auth(
    secrets: Optional[Mapping[str, Any]] = None,
    environ: Optional[Mapping[str, str]] = None,
) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
    sources = []
    if secrets is not None:
        for key_name in TMDB_ALL_KEY_NAMES:
            sources.append((key_name, _read_mapping_value(secrets, key_name)))

        nested_tmdb = _read_mapping_value(secrets, "tmdb") or _read_mapping_value(secrets, "TMDB")
        if isinstance(nested_tmdb, Mapping):
            for key_name in TMDB_ALL_KEY_NAMES:
                sources.append((key_name, nested_tmdb.get(key_name)))

    env_values = environ if environ is not None else os.environ
    for key_name in TMDB_ALL_KEY_NAMES:
        sources.append((key_name, env_values.get(key_name)))

    saw_invalid = False
    for key_name, raw_value in sources:
        parsed, error = parse_tmdb_credential(raw_value, key_name)
        if parsed:
            return parsed, None
        if error == "invalid":
            saw_invalid = True

    if saw_invalid:
        return None, "invalid"
    return None, None


def fetch_poster(
    movie_id: Any,
    auth_config: Optional[Dict[str, str]],
    poster_base_url: str,
    placeholder_image: str,
    timeout_seconds: int,
) -> Tuple[str, Optional[str]]:
    if not auth_config:
        return placeholder_image, "missing_auth"

    params = {"language": "en-US"}
    headers = {"Accept": "application/json"}

    if auth_config["mode"] == "api_key":
        params["api_key"] = auth_config["value"]
    else:
        headers["Authorization"] = "Bearer " + auth_config["value"]

    url = TMDB_MOVIE_DETAILS_URL.format(movie_id=movie_id)
    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout_seconds)
    except requests.Timeout:
        return placeholder_image, "timeout"
    except requests.RequestException:
        return placeholder_image, "request_error"

    if response.status_code in (401, 403):
        return placeholder_image, "auth_error"
    if response.status_code == 429:
        return placeholder_image, "rate_limited"
    if response.status_code == 404:
        return placeholder_image, "not_found"
    if response.status_code >= 400:
        return placeholder_image, "http_error"

    try:
        data = response.json()
    except ValueError:
        return placeholder_image, "invalid_response"

    if not isinstance(data, dict):
        return placeholder_image, "invalid_response"

    poster_path = data.get("poster_path")
    if isinstance(poster_path, str) and poster_path.strip():
        normalized_path = poster_path if poster_path.startswith("/") else f"/{poster_path.lstrip('/')}"
        return f"{poster_base_url}{normalized_path}", None

    return placeholder_image, "no_poster"
