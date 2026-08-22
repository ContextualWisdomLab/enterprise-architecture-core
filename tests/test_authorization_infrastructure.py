"""Availability regressions for Keyverse signature verification infrastructure."""

from __future__ import annotations

import subprocess
from typing import Any

import pytest

from ea_core_foundation.authorization import AuthorizationError, verify_rs256_signature

_MINIMAL_RSA_JWK = {
    "kty": "RSA",
    "alg": "RS256",
    "use": "sig",
    "n": "AQ",
    "e": "Aw",
}


@pytest.mark.parametrize(
    "infrastructure_error",
    [FileNotFoundError("openssl"), subprocess.TimeoutExpired("openssl", 3)],
)
def test_rs256_infrastructure_failure_is_service_unavailable(
    infrastructure_error: OSError | subprocess.TimeoutExpired,
) -> None:
    """Missing or hung verification infrastructure must not mimic bad JWTs."""

    def failing_runner(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        del args, kwargs
        raise infrastructure_error

    with pytest.raises(AuthorizationError) as captured:
        verify_rs256_signature(
            b"header.payload",
            b"signature",
            _MINIMAL_RSA_JWK,
            runner=failing_runner,
        )

    assert captured.value.error_code == "planner_unavailable"
    assert captured.value.http_status == 503
    assert "verification infrastructure" in str(captured.value)
