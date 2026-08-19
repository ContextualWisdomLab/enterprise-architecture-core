"""Verify repository-owned workflows preserve truthful integration evidence."""

from __future__ import annotations

import re
from pathlib import Path

_WORKFLOW_PATHS = (
    Path(".github/workflows/ci.yml"),
    Path(".github/workflows/runtime-readiness.yml"),
    Path(".github/workflows/supply-chain.yml"),
)
_PUSH_BRANCHES_PATTERN = re.compile(
    r"(?m)^  push:\n    branches: \[([^\]]+)\]$"
)
_CI_PATH = Path(".github/workflows/ci.yml")
_SUPPLY_CHAIN_PATH = Path(".github/workflows/supply-chain.yml")


def _push_branches(workflow_path: Path) -> set[str]:
    """Return the explicit push branches declared by one repository workflow."""
    workflow_text = workflow_path.read_text(encoding="utf-8")
    match = _PUSH_BRANCHES_PATTERN.search(workflow_text)
    assert match is not None, f"{workflow_path} must declare explicit push branches"
    return {
        branch.strip()
        for branch in match.group(1).split(",")
        if branch.strip()
    }


def test_repository_workflows_run_on_git_flow_integration_branches() -> None:
    """Require post-integration evidence on both develop and stable main pushes."""
    expected_branches = {"develop", "main"}
    for workflow_path in _WORKFLOW_PATHS:
        assert _push_branches(workflow_path) == expected_branches


def test_dependency_lock_name_matches_the_default_checkout_commit() -> None:
    """Do not label merge-candidate dependency bytes with the PR source-head SHA."""
    workflow_text = _CI_PATH.read_text(encoding="utf-8")

    assert "name: uv-lock-${{ github.sha }}" in workflow_text
    assert "github.event.pull_request.head.sha || github.sha" not in workflow_text


def test_package_evidence_name_matches_the_default_checkout_commit() -> None:
    """Do not label merge-candidate package bytes with the PR source-head SHA."""
    workflow_text = _SUPPLY_CHAIN_PATH.read_text(encoding="utf-8")

    assert "name: package-evidence-${{ github.sha }}" in workflow_text
    assert "github.event.pull_request.head.sha || github.sha" not in workflow_text
