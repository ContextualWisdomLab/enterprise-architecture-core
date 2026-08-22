"""Regression coverage for JWS critical protected-header handling."""

from __future__ import annotations

from typing import Any

import pytest

import ea_core_foundation.authorization as authorization
from tests.test_authorization_hardening import (
    _accept_signature,
    _config,
    _jwks_loader,
    _token,
)


@pytest.mark.parametrize(
    "header",
    [
        {
            "alg": "RS256",
            "kid": "key-1",
            "typ": "JWT",
            "crit": ["https://example.invalid/jws-extension"],
            "https://example.invalid/jws-extension": True,
        },
        {"alg": "RS256", "kid": "key-1", "typ": "JWT", "crit": []},
        {
            "alg": "RS256",
            "kid": "key-1",
            "typ": "JWT",
            "crit": "not-an-array",
        },
    ],
)
def test_unsupported_or_malformed_critical_headers_fail_closed(
    header: dict[str, Any],
) -> None:
    """Reject every ``crit`` form because EA Core supports no JWS extensions."""

    with pytest.raises(authorization.AuthorizationError, match="critical"):
        authorization.verify_keyverse_bearer(
            f"Bearer {_token(header=header)}",
            _config(),
            jwks_loader=_jwks_loader,
            signature_verifier=_accept_signature,
            now_epoch=1_800_000_000,
        )
