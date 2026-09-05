"""Regression tests for strict reassessment request-target parsing."""

from __future__ import annotations

import pytest

from ea_core_foundation.data_management_recheck import parse_data_management_recheck_request
from ea_core_foundation.service import PlannerRequestError
from tests.test_data_management_recheck_api import _PATH, _payload


def test_recheck_rejects_matrix_parameters_in_request_target() -> None:
    """Matrix parameters cannot be discarded while binding a governed route."""

    with pytest.raises(PlannerRequestError, match="recheck path"):
        parse_data_management_recheck_request(
            _PATH + ";unexpected=1",
            _payload(),
        )
