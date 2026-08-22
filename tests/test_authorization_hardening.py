"""Hostile-input and fail-closed tests for the Keyverse authorization boundary."""

from __future__ import annotations

import base64
import json
import subprocess
from typing import Any

import pytest

import ea_core_foundation.authorization as authorization

_ISSUER = "https://id.example/realms/cwl"
_JWKS_URL = f"{_ISSUER}/protocol/openid-connect/certs"
_TENANT = "018f47b2-905a-7b16-bfd4-7e4f53f10e91"


def _b64url(value: bytes) -> str:
    """Return one unpadded base64url test segment."""

    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _token(
    *,
    header: Any = None,
    claims: Any = None,
    signature: bytes = b"signature",
) -> str:
    """Build a JWT-shaped value whose cryptographic result can be injected."""

    if header is None:
        header = {"alg": "RS256", "kid": "key-1", "typ": "JWT"}
    if claims is None:
        claims = {
            "iss": _ISSUER,
            "aud": "enterprise-architecture-core",
            "exp": 2_000_000_000,
            "sub": "reader-1",
            "tenant": _TENANT,
            "role": "ea_reader",
        }
    return ".".join(
        (
            _b64url(json.dumps(header, separators=(",", ":")).encode()),
            _b64url(json.dumps(claims, separators=(",", ":")).encode()),
            _b64url(signature),
        )
    )


def _config() -> authorization.KeyverseAuthorizationConfig:
    """Return a strict authorization profile used across negative tests."""

    return authorization.KeyverseAuthorizationConfig(
        issuer_uri=_ISSUER,
        audience="enterprise-architecture-core",
        jwks_url=_JWKS_URL,
        tenant_claim="tenant",
        role_claim="role",
        allowed_roles=frozenset({"ea_reader"}),
    )


def _jwks_loader(url: str, issuer: str) -> dict[str, Any]:
    """Return exactly one structurally usable test signing key."""

    assert (url, issuer) == (_JWKS_URL, _ISSUER)
    return {
        "keys": [
            {
                "kid": "key-1",
                "kty": "RSA",
                "alg": "RS256",
                "use": "sig",
                "n": _b64url(b"\x80" + b"n" * 255),
                "e": _b64url(b"\x01\x00\x01"),
            }
        ]
    }


def _accept_signature(
    signing_input: bytes, signature: bytes, jwk: Any
) -> bool:
    """Accept signature wiring so claim validation can be tested independently."""

    assert signing_input and signature and jwk["kid"] == "key-1"
    return True


@pytest.mark.parametrize(
    ("issuer", "jwks"),
    [
        ("http://id.example/realms/cwl", _JWKS_URL),
        (_ISSUER, "http://id.example/realms/cwl/protocol/openid-connect/certs"),
        ("https://user@id.example/realms/cwl", _JWKS_URL),
        (_ISSUER, "https://user@id.example/realms/cwl/certs"),
        (_ISSUER, "https://other.example/realms/cwl/certs"),
        (_ISSUER, "https://id.example:444/realms/cwl/certs"),
        (_ISSUER, f"{_JWKS_URL}?redirect=x"),
        (_ISSUER, f"{_JWKS_URL}#fragment"),
        ("https://id.example", "https://id.example/certs"),
        (_ISSUER, "https://id.example/not-the-issuer/certs"),
        ("https://id.example:bad/realms/cwl", _JWKS_URL),
    ],
)
def test_jwks_configuration_rejects_unsafe_locations(
    issuer: str, jwks: str
) -> None:
    """Operator configuration cannot turn JWKS lookup into an SSRF redirector."""

    assert authorization._same_origin_jwks(issuer, jwks) is False


def test_config_rejects_complete_but_unsafe_jwks() -> None:
    """Complete environment variables still fail closed on an unsafe origin."""

    assert (
        authorization.build_keyverse_authorization_config(
            {
                "EA_OIDC_ISSUER": _ISSUER,
                "EA_OIDC_AUDIENCE": "enterprise-architecture-core",
                "EA_OIDC_JWKS_URL": "https://evil.example/certs",
                "EA_TENANT_CLAIM": "tenant",
                "EA_ROLE_CLAIM": "role",
                "EA_READ_ROLES": " ea_reader, ,ea_architect ",
            }
        )
        is None
    )


def test_strict_json_helpers_reject_ambiguous_input() -> None:
    """Duplicate names, constants, malformed base64, and non-objects fail closed."""

    with pytest.raises(ValueError, match="duplicate JSON member"):
        authorization._reject_duplicate_members([("a", 1), ("a", 2)])
    with pytest.raises(ValueError, match="non-standard JSON constant"):
        authorization._reject_json_constant("NaN")
    for value in ("", "abc=", "%"):
        with pytest.raises(authorization.AuthorizationError):
            authorization._decode_base64url(value, "fixture")
    for raw in (b"\xff", b"{", b"[]", b'{"a":1,"a":2}', b'{"a":NaN}'):
        with pytest.raises(authorization.AuthorizationError):
            authorization._decode_json_object(_b64url(raw), "fixture")


def test_redirect_handler_never_follows_jwks_redirects() -> None:
    """A Keyverse endpoint cannot redirect the service to another network target."""

    handler = authorization._NoRedirectHandler()
    assert (
        handler.redirect_request(
            object(), object(), 302, "found", {}, "https://evil.example"
        )
        is None
    )


class _FakeResponse:
    """Minimal bounded HTTP response for JWKS loader tests."""

    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, amount: int) -> bytes:
        assert amount == authorization._MAX_JWKS_BYTES + 1
        return self.payload


class _FakeOpener:
    """Return or fail one deterministic JWKS response."""

    def __init__(
        self,
        payload: bytes | None = None,
        error: Exception | None = None,
    ) -> None:
        self.payload = payload
        self.error = error

    def open(self, request: Any, timeout: int) -> _FakeResponse:
        assert request.full_url == _JWKS_URL
        assert timeout == 3
        if self.error is not None:
            raise self.error
        assert self.payload is not None
        return _FakeResponse(self.payload)


def test_jwks_loader_bounds_and_validates_remote_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Network, size, encoding, shape, and duplicate-key failures are non-passing."""

    with pytest.raises(authorization.AuthorizationError, match="outside"):
        authorization.load_keyverse_jwks("https://evil.example/certs", _ISSUER)

    for payload, error_pattern in (
        (b"x" * (authorization._MAX_JWKS_BYTES + 1), "bounded"),
        (b"\xff", "valid JSON"),
        (b"{", "valid JSON"),
        (b'{"keys":[],"keys":[]}', "valid JSON"),
        (b'{"value":NaN}', "valid JSON"),
        (b"[]", "JSON object"),
    ):
        monkeypatch.setattr(
            authorization.urllib.request,
            "build_opener",
            lambda *args, payload=payload: _FakeOpener(payload=payload),
        )
        with pytest.raises(authorization.AuthorizationError, match=error_pattern):
            authorization.load_keyverse_jwks(_JWKS_URL, _ISSUER)

    monkeypatch.setattr(
        authorization.urllib.request,
        "build_opener",
        lambda *args: _FakeOpener(error=OSError("network down")),
    )
    with pytest.raises(authorization.AuthorizationError, match="unavailable"):
        authorization.load_keyverse_jwks(_JWKS_URL, _ISSUER)

    monkeypatch.setattr(
        authorization.urllib.request,
        "build_opener",
        lambda *args: _FakeOpener(payload=b'{"keys":[]}'),
    )
    assert authorization.load_keyverse_jwks(_JWKS_URL, _ISSUER) == {"keys": []}


def test_der_and_rsa_key_builders_fail_closed_on_invalid_keys() -> None:
    """RSA/JWK conversion rejects zero, wrong-purpose, and incomplete key material."""

    assert authorization._der_length(127) == b"\x7f"
    assert authorization._der_length(128) == b"\x81\x80"
    with pytest.raises(authorization.AuthorizationError, match="positive"):
        authorization._der_integer(b"\x00")
    assert authorization._der_integer(b"\x80").startswith(b"\x02\x02\x00\x80")
    assert authorization._der_sequence(b"x") == b"\x30\x01x"

    for jwk, message in (
        ({"kty": "EC", "alg": "RS256"}, "RS256 RSA"),
        ({"kty": "RSA", "alg": "HS256"}, "RS256 RSA"),
        ({"kty": "RSA", "alg": "RS256", "use": "enc"}, "signing key"),
        ({"kty": "RSA", "alg": "RS256", "use": "sig"}, "modulus"),
    ):
        with pytest.raises(authorization.AuthorizationError, match=message):
            authorization._rsa_public_key_pem(jwk)

    jwk = _jwks_loader(_JWKS_URL, _ISSUER)["keys"][0]
    pem = authorization._rsa_public_key_pem(jwk)
    assert pem.startswith(b"-----BEGIN PUBLIC KEY-----")


def test_signature_runner_failures_are_non_passing() -> None:
    """Verifier outages are 503 while negative signatures remain unauthorized."""

    jwk = _jwks_loader(_JWKS_URL, _ISSUER)["keys"][0]

    def os_failure(*args: Any, **kwargs: Any) -> Any:
        raise OSError("openssl missing")

    def timeout_failure(*args: Any, **kwargs: Any) -> Any:
        raise subprocess.TimeoutExpired("openssl", 3)

    def rejected(
        command: list[str], **kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 1, "", "bad signature")

    def accepted(
        command: list[str], **kwargs: Any
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, "Verified OK", "")

    for failing_runner in (os_failure, timeout_failure):
        with pytest.raises(authorization.AuthorizationError) as captured:
            authorization.verify_rs256_signature(
                b"a.b", b"sig", jwk, runner=failing_runner
            )
        assert captured.value.error_code == "planner_unavailable"
        assert captured.value.http_status == 503

    assert not authorization.verify_rs256_signature(
        b"a.b", b"sig", jwk, runner=rejected
    )
    assert authorization.verify_rs256_signature(
        b"a.b", b"sig", jwk, runner=accepted
    )


def test_signing_key_selection_and_audience_shapes_are_exact() -> None:
    """Ambiguous keys and malformed multi-audience claims do not pass."""

    for jwks in ({"keys": "bad"}, {"keys": []}, {"keys": [{"kid": "other"}]}):
        with pytest.raises(authorization.AuthorizationError):
            authorization._select_signing_key(jwks, "key-1")
    with pytest.raises(authorization.AuthorizationError, match="ambiguous"):
        authorization._select_signing_key(
            {"keys": [{"kid": "key-1"}, {"kid": "key-1"}]},
            "key-1",
        )
    assert authorization._audience_contains(
        ["other", "enterprise-architecture-core"], "enterprise-architecture-core"
    )
    assert not authorization._audience_contains(
        ["enterprise-architecture-core", 7], "enterprise-architecture-core"
    )
    assert not authorization._audience_contains(7, "enterprise-architecture-core")


def test_bearer_parser_rejects_structural_and_header_drift() -> None:
    """Malformed bearer syntax and JWT algorithm/key/type drift fail before claims."""

    for header_value in (None, "Basic abc", "Bearer one.two", "Bearer one..three"):
        with pytest.raises(authorization.AuthorizationError):
            authorization.verify_keyverse_bearer(
                header_value,
                _config(),
                jwks_loader=_jwks_loader,
                signature_verifier=_accept_signature,
                now_epoch=1_800_000_000,
            )

    for header in (
        {"alg": "HS256", "kid": "key-1"},
        {"alg": "RS256"},
        {"alg": "RS256", "kid": "", "typ": "JWT"},
        {"alg": "RS256", "kid": "key-1", "typ": "opaque"},
    ):
        with pytest.raises(authorization.AuthorizationError):
            authorization.verify_keyverse_bearer(
                f"Bearer {_token(header=header)}",
                _config(),
                jwks_loader=_jwks_loader,
                signature_verifier=_accept_signature,
                now_epoch=1_800_000_000,
            )


def test_bearer_claim_validation_covers_temporal_and_identity_edges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Audience lists, nbf, subject, tenant, and role keep exact fail-closed meaning."""

    baseline = {
        "iss": _ISSUER,
        "aud": ["other", "enterprise-architecture-core"],
        "exp": 2_000_000_000,
        "sub": "reader-1",
        "tenant": _TENANT,
        "role": "ea_reader",
        "nbf": 1_700_000_000,
    }
    monkeypatch.setattr(authorization.time, "time", lambda: 1_800_000_000)
    context = authorization.verify_keyverse_bearer(
        f"Bearer {_token(claims=baseline)}",
        _config(),
        jwks_loader=_jwks_loader,
        signature_verifier=_accept_signature,
    )
    assert str(context.tenant_record_id) == _TENANT

    invalid_claims = (
        ({**baseline, "exp": True}, "expiration"),
        ({**baseline, "exp": "later"}, "expiration"),
        ({**baseline, "nbf": True}, "not yet valid"),
        ({**baseline, "nbf": 1_900_000_000}, "not yet valid"),
        ({**baseline, "sub": ""}, "subject"),
        ({**baseline, "sub": 7}, "subject"),
        ({**baseline, "tenant": 7}, "tenant"),
        ({**baseline, "role": 7}, "role"),
    )
    for claims, message in invalid_claims:
        with pytest.raises(authorization.AuthorizationError, match=message):
            authorization.verify_keyverse_bearer(
                f"Bearer {_token(claims=claims)}",
                _config(),
                jwks_loader=_jwks_loader,
                signature_verifier=_accept_signature,
                now_epoch=1_800_000_000,
            )
