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
_EXACT_SOURCE_SHA = "${{ github.event.pull_request.head.sha || github.sha }}"


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


def test_pull_request_workflows_checkout_and_verify_exact_source_head() -> None:
    """Prevent synthetic pull-request merge refs from masquerading as source evidence."""
    exact_ref = f"ref: {_EXACT_SOURCE_SHA}"
    exact_expected_sha = f"EXPECTED_SHA: {_EXACT_SOURCE_SHA}"
    exact_verification = 'run: test "$(git rev-parse HEAD)" = "$EXPECTED_SHA"'

    for workflow_path in _WORKFLOW_PATHS:
        workflow_text = workflow_path.read_text(encoding="utf-8")
        checkout_count = workflow_text.count("uses: actions/checkout@")
        assert checkout_count > 0, workflow_path
        assert workflow_text.count(exact_ref) == checkout_count, workflow_path
        assert workflow_text.count(exact_expected_sha) == checkout_count, workflow_path
        assert workflow_text.count(exact_verification) == checkout_count, workflow_path


def test_dependency_lock_name_matches_the_exact_source_commit() -> None:
    """Bind dependency-lock evidence to the source revision actually checked out."""
    workflow_text = _CI_PATH.read_text(encoding="utf-8")

    assert f"name: uv-lock-{_EXACT_SOURCE_SHA}" in workflow_text


def test_package_evidence_name_matches_the_exact_source_commit() -> None:
    """Bind package evidence to the source revision actually checked out."""
    workflow_text = _SUPPLY_CHAIN_PATH.read_text(encoding="utf-8")

    assert f"name: package-evidence-{_EXACT_SOURCE_SHA}" in workflow_text
