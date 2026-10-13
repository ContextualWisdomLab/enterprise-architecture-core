"""Security regressions for configured Keyverse JWKS path confinement."""

import pytest

import ea_core_foundation.authorization as authorization

_ISSUER = "https://id.example/realms/cwl"


@pytest.mark.parametrize(
    "jwks_url",
    [
        "https://id.example/realms/cwl/../other/certs",
        "https://id.example/realms/cwl/%2e%2e/other/certs",
        "https://id.example/realms/cwl/./protocol/openid-connect/certs",
        "https://id.example/realms/cwl/%2e/protocol/openid-connect/certs",
        "https://id.example/realms/cwl/%2E%2E/other/certs",
    ],
)
def test_jwks_scope_rejects_path_normalization_escapes(jwks_url: str) -> None:
    """Dot-segment aliases cannot escape or ambiguously rewrite issuer scope."""

    assert authorization._same_origin_jwks(_ISSUER, jwks_url) is False
