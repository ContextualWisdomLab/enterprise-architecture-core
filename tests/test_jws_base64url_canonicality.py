"""JWS compact serialization must use canonical unpadded base64url segments."""

from __future__ import annotations

import base64
import json
from typing import Any

import pytest

import ea_core_foundation.authorization as authorization

_ISSUER = "https://id.example/realms/cwl"
_TENANT = "018f47b2-905a-7b16-bfd4-7e4f53f10e91"


def _b64url(value: bytes) -> str:
    """Encode one canonical unpadded base64url test segment."""

    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _config() -> authorization.KeyverseAuthorizationConfig:
    """Return the exact relying-party configuration used by this regression."""

    return authorization.KeyverseAuthorizationConfig(
        issuer_uri=_ISSUER,
        audience="enterprise-architecture-core",
        jwks_url=f"{_ISSUER}/protocol/openid-connect/certs",
        tenant_claim="tenant",
        role_claim="role",
        allowed_roles=frozenset({"ea_reader"}),
    )


def _jwks_loader(url: str, issuer: str) -> dict[str, Any]:
    """Return the one key selected by the protected JWS header."""

    assert url == f"{_ISSUER}/protocol/openid-connect/certs"
    assert issuer == _ISSUER
    return {"keys": [{"kid": "key-1"}]}


def _accept_signature(
    signing_input: bytes, signature: bytes, jwk: Any
) -> bool:
    """Isolate compact-serialization admission from cryptographic validity."""

    assert signing_input
    assert signature in {b"\xfb", b"\xff"}
    assert jwk["kid"] == "key-1"
    return True


def _token_with_signature_segment(signature_segment: str) -> str:
    """Build an otherwise valid access token with a caller-selected signature text."""

    header = _b64url(
        json.dumps(
            {"alg": "RS256", "kid": "key-1", "typ": "JWT"},
            separators=(",", ":"),
        ).encode("utf-8")
    )
    claims = _b64url(
        json.dumps(
            {
                "iss": _ISSUER,
                "aud": "enterprise-architecture-core",
                "exp": 2_000_000_000,
                "sub": "reader-1",
                "tenant": _TENANT,
                "role": "ea_reader",
            },
            separators=(",", ":"),
        ).encode("utf-8")
    )
    return f"{header}.{claims}.{signature_segment}"


@pytest.mark.parametrize("signature_segment", ["+w", "/w"])
def test_bearer_rejects_standard_base64_characters_in_jws_segments(
    signature_segment: str,
) -> None:
    """JWS compact serialization rejects '+' and '/' instead of accepting aliases."""

    with pytest.raises(authorization.AuthorizationError, match="canonical base64url"):
        authorization.verify_keyverse_bearer(
            f"Bearer {_token_with_signature_segment(signature_segment)}",
            _config(),
            jwks_loader=_jwks_loader,
            signature_verifier=_accept_signature,
            now_epoch=1_800_000_000,
        )


@pytest.mark.parametrize(("segment", "decoded"), [("-w", b"\xfb"), ("_w", b"\xff")])
def test_base64url_decoder_keeps_url_safe_alphabet(
    segment: str, decoded: bytes
) -> None:
    """The exact URL-safe spellings remain accepted after fail-closed hardening."""

    assert authorization._decode_base64url(segment, "fixture") == decoded
