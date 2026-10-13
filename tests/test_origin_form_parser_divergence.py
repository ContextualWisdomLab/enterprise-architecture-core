"""Defensive exact-target parsing remains fail closed on parser divergence."""

from urllib.parse import ParseResult

import pytest

from ea_core_foundation import decision_plane_http


def test_origin_form_rejects_parser_route_divergence(monkeypatch) -> None:
    """A changed URL parser cannot bind a different route than the raw target."""
    monkeypatch.setattr(
        decision_plane_http,
        "urlparse",
        lambda target: ParseResult("", "", "/different-route", "", "", ""),
    )
    with pytest.raises(
        decision_plane_http.PlannerRequestError, match="local origin form"
    ):
        decision_plane_http.parse_origin_form_target(
            "/exact-route", "synthetic parser control", query_allowed=False
        )
