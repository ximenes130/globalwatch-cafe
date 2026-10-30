"""Cliente do Supabase Storage, com a rede substituída (T2.10, R6.4)."""

import io
import json
import urllib.error
import urllib.request
from uuid import UUID

import pytest

from app.storage import StorageError, SupabaseStorage, object_prefix

URL = "https://proj.supabase.co"


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


@pytest.fixture
def sent(monkeypatch):
    requests = []
    replies = []

    def fake_urlopen(request, timeout):
        requests.append(request)
        reply = replies.pop(0) if replies else b""
        if isinstance(reply, Exception):
            raise reply
        return Response(reply)

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    return requests, replies


def storage(key: str = "eyJhbGciOi.jwt.antigo") -> SupabaseStorage:
    return SupabaseStorage(URL, key, "analyses", ttl_seconds=300)


def test_object_prefix_is_user_then_analysis():
    user = UUID("11111111-1111-1111-1111-111111111111")
    analysis = UUID("22222222-2222-2222-2222-222222222222")

    assert object_prefix(user, analysis) == f"{user}/{analysis}"


def test_upload_request(sent):
    requests, _ = sent

    storage().upload("u/a/rgb.png", b"png", "image/png")

    request = requests[0]
    assert request.get_method() == "POST"
    assert request.full_url == f"{URL}/storage/v1/object/analyses/u/a/rgb.png"
    assert request.data == b"png"
    assert request.get_header("Content-type") == "image/png"
    assert request.get_header("X-upsert") == "true"


def test_legacy_jwt_key_goes_in_both_headers(sent):
    requests, _ = sent

    storage("eyJhbGciOi.jwt.antigo").upload("p", b"", "image/png")

    assert requests[0].get_header("Apikey") == "eyJhbGciOi.jwt.antigo"
    assert requests[0].get_header("Authorization") == "Bearer eyJhbGciOi.jwt.antigo"


def test_new_secret_key_goes_only_in_apikey(sent):
    requests, _ = sent

    storage("sb_secret_abc").upload("p", b"", "image/png")

    assert requests[0].get_header("Apikey") == "sb_secret_abc"
    assert requests[0].get_header("Authorization") is None


def test_signed_urls_expire_in_five_minutes(sent):
    requests, replies = sent
    replies.append(
        json.dumps(
            [{"path": "u/a/rgb.png", "signedURL": "/object/sign/analyses/u/a/rgb.png?token=t"}]
        ).encode()
    )

    urls = storage().signed_urls(["u/a/rgb.png"])

    body = json.loads(requests[0].data)
    assert body == {"expiresIn": 300, "paths": ["u/a/rgb.png"]}
    assert requests[0].full_url == f"{URL}/storage/v1/object/sign/analyses"
    assert urls == {"u/a/rgb.png": f"{URL}/storage/v1/object/sign/analyses/u/a/rgb.png?token=t"}


def test_missing_signed_url_is_an_error(sent):
    _, replies = sent
    replies.append(json.dumps([{"path": "x", "error": "Not found", "signedURL": None}]).encode())

    with pytest.raises(StorageError, match="Sem URL assinada"):
        storage().signed_urls(["x"])


def test_remove_request(sent):
    requests, _ = sent

    storage().remove(["u/a/rgb.png", "u/a/result.geojson"])

    assert requests[0].get_method() == "DELETE"
    assert requests[0].full_url == f"{URL}/storage/v1/object/analyses"
    assert json.loads(requests[0].data) == {"prefixes": ["u/a/rgb.png", "u/a/result.geojson"]}


def test_http_and_network_errors_become_storage_error(sent):
    _, replies = sent
    replies.append(
        urllib.error.HTTPError(URL, 403, "Forbidden", {}, io.BytesIO(b'{"error":"denied"}'))
    )
    replies.append(urllib.error.URLError("sem rede"))

    with pytest.raises(StorageError, match="403"):
        storage().upload("p", b"", "image/png")
    with pytest.raises(StorageError, match="inacessível"):
        storage().upload("p", b"", "image/png")
