"""Regression tests for the foundation API/event specification surface."""


def test_foundation_openapi_exposes_only_implemented_health_surface(
    openapi_document,
) -> None:
    """Unimplemented CRUD commands are not advertised as callable contracts."""
    assert openapi_document["openapi"] == "3.2.0"
    assert set(openapi_document["paths"]) == {"/health"}
    assert set(openapi_document["paths"]["/health"]) == {"get"}


def test_foundation_asyncapi_tracks_current_stable_minor(asyncapi_document) -> None:
    """The event document uses the accepted current AsyncAPI minor version."""
    assert asyncapi_document["asyncapi"] == "3.1.0"
