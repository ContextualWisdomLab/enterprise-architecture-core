"""Public API documentation tests."""

import inspect

import ea_core_foundation


def test_public_api_is_versioned_and_documented() -> None:
    """All exported foundation symbols carry public documentation."""

    assert ea_core_foundation.__version__ == "0.1.0"
    for symbol_name in ea_core_foundation.__all__:
        assert inspect.getdoc(getattr(ea_core_foundation, symbol_name)), symbol_name
