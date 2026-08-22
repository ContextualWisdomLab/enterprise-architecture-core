"""Availability regression for Keyverse JWKS retrieval infrastructure."""

from __future__ import annotations

from typing import Any

import pytest

import ea_core_foundation.authorization as authorization

_ISSUER = "https://id.example/realms/cwl"
_JWKS_URL = f"{_ISSUER}/protocol/openid-connect/certs"


class _UnavailableOpener:
    """Simulate an unavailable Keyverse JWKS transport."""

    def open(self, request: Any, timeout: int) -> Any:
        """Raise the same transport failure as the production URL opener."""

        assert request.full_url == _JWKS_URL
        assert timeout == 3
        raise OSError("network unavailable")


def test_jwks_transport_outage_is_service_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A Keyverse transport outage must not masquerade as invalid credentials."""

    monkeypatch.setattr(
        authorization.urllib.request,
        "build_opener",
        lambda *args: _UnavailableOpener(),
    )

    with pytest.raises(authorization.AuthorizationError) as captured:
        authorization.load_keyverse_jwks(_JWKS_URL, _ISSUER)

    assert captured.value.error_code == "planner_unavailable"
    assert captured.value.http_status == 503
    assert "signing keys" in str(captured.value)
