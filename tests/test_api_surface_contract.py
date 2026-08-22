"""Regression tests for the implemented API/event specification surface."""


def test_openapi_exposes_only_implemented_process_and_planner_surface(
    openapi_document,
) -> None:
    """Only executable probes and the authenticated planner are advertised."""

    assert openapi_document["openapi"] == "3.2.0"
    planner_path = "/v1/technology-target-state-plans/{technology_version_id}"
    assert set(openapi_document["paths"]) == {"/health", "/ready", planner_path}
    assert set(openapi_document["paths"]["/health"]) == {"get"}
    assert set(openapi_document["paths"]["/ready"]) == {"get"}
    assert set(openapi_document["paths"][planner_path]) == {"get"}


def test_foundation_asyncapi_tracks_current_stable_minor(asyncapi_document) -> None:
    """The event document uses the accepted current AsyncAPI minor version."""

    assert asyncapi_document["asyncapi"] == "3.1.0"
