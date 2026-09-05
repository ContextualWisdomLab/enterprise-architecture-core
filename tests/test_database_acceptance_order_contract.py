"""Guard intentional ordering for stateful PostgreSQL acceptance scenarios."""

from __future__ import annotations

from pathlib import Path

_CI_WORKFLOW = Path(".github/workflows/ci.yml")
_TEST_STRATEGY = Path("docs/TEST_STRATEGY.md")
_STATEFUL_DATA_MANAGEMENT_SCENARIO = (
    Path("database/tests/zzzzzzzzzzzzz_verify_data_management_improvement.sql"),
    Path(
        "database/tests/"
        "zzzzzzzzzzzzzz_verify_data_management_replay_after_supersession.sql"
    ),
    Path("database/tests/zzzzzzzzzzzzzzzzzzzzz_verify_data_management_dependencies.sql"),
)
_REASSESSMENT_REPLAY_SCENARIO = (
    Path("database/tests/zzzzzzzzzzzzz_verify_data_management_improvement.sql"),
    Path("database/tests/zzzzzzzzzzzzzzzzzzz_verify_data_management_recheck.sql"),
    Path(
        "database/tests/"
        "zzzzzzzzzzzzzzzzzzzz_verify_data_management_recheck_runtime_port.sql"
    ),
    Path(
        "database/tests/"
        "zzzzzzzzzzzzzzzzzzzzzzzzzzzz_verify_data_management_recheck_replay_receipt.sql"
    ),
)


def test_stateful_data_management_acceptance_order_is_executable_contract() -> None:
    """Keep the documented committed-history scenario aligned with CI glob order."""
    for acceptance_path in _STATEFUL_DATA_MANAGEMENT_SCENARIO:
        assert acceptance_path.is_file(), f"missing acceptance stage: {acceptance_path}"

    assert tuple(sorted(_STATEFUL_DATA_MANAGEMENT_SCENARIO)) == (
        _STATEFUL_DATA_MANAGEMENT_SCENARIO
    )

    workflow_text = _CI_WORKFLOW.read_text(encoding="utf-8")
    assert "for acceptance_path in database/tests/*.sql; do" in workflow_text

    strategy_text = _TEST_STRATEGY.read_text(encoding="utf-8")
    assert "lexicographic acceptance scenario" in strategy_text
    for acceptance_path in _STATEFUL_DATA_MANAGEMENT_SCENARIO:
        assert f"`{acceptance_path}`" in strategy_text


def test_reassessment_replay_acceptance_order_is_executable_contract() -> None:
    """Keep reassessment replay fixtures explicit instead of relying on hidden order."""
    for acceptance_path in _REASSESSMENT_REPLAY_SCENARIO:
        assert acceptance_path.is_file(), f"missing reassessment stage: {acceptance_path}"

    assert tuple(sorted(_REASSESSMENT_REPLAY_SCENARIO)) == _REASSESSMENT_REPLAY_SCENARIO

    workflow_text = _CI_WORKFLOW.read_text(encoding="utf-8")
    assert "for acceptance_path in database/tests/*.sql; do" in workflow_text

    strategy_text = _TEST_STRATEGY.read_text(encoding="utf-8")
    assert "reassessment replay acceptance sequence" in strategy_text
    for acceptance_path in _REASSESSMENT_REPLAY_SCENARIO:
        assert f"`{acceptance_path}`" in strategy_text
