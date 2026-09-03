"""Regression contracts for repository-owned GitHub workflow execution."""

import re
from pathlib import Path

WORKFLOW_PATHS = (
    Path(".github/workflows/ci.yml"),
    Path(".github/workflows/runtime-readiness.yml"),
    Path(".github/workflows/supply-chain.yml"),
)
CI_WORKFLOW_PATH = Path(".github/workflows/ci.yml")
PYPROJECT_PATH = Path("pyproject.toml")


def test_hosted_workflows_pin_supported_runner_image() -> None:
    """Require an explicit hosted image instead of the starving latest alias."""
    for workflow_path in WORKFLOW_PATHS:
        workflow = workflow_path.read_text(encoding="utf-8")
        labels = [
            line.split(":", 1)[1].strip().split()[0]
            for line in workflow.splitlines()
            if line.lstrip().startswith("runs-on:")
        ]
        assert labels, f"{workflow_path} must declare at least one runs-on label"
        assert set(labels) == {"ubuntu-24.04"}, (
            f"{workflow_path} must pin ubuntu-24.04; observed runner labels: {labels}"
        )


def test_ci_exercises_every_declared_python_minor() -> None:
    """Keep CI aligned with every Python minor advertised by package metadata."""
    pyproject = PYPROJECT_PATH.read_text(encoding="utf-8")
    declared_versions = set(
        re.findall(r'Programming Language :: Python :: (3\.\d+)"', pyproject)
    )
    assert declared_versions

    workflow = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    matrix_match = re.search(r"python-version:\s*\[([^\]]+)\]", workflow)
    assert matrix_match is not None, "ci must use a Python-version matrix"
    workflow_versions = set(re.findall(r'"(3\.\d+)"', matrix_match.group(1)))
    assert workflow_versions == declared_versions


def test_ci_postgres_service_is_digest_pinned() -> None:
    """Keep the real-PostgreSQL CI service reproducible at an immutable image."""
    workflow = CI_WORKFLOW_PATH.read_text(encoding="utf-8")
    assert re.search(
        r"image:\s+postgres:18\.4@sha256:[0-9a-f]{64}\b",
        workflow,
    ), "ci PostgreSQL 18.4 service must be pinned by sha256 digest"


def test_workflow_hex_action_revisions_are_full_commit_shas() -> None:
    """Reject truncated hexadecimal action revisions that cannot identify a commit."""
    for workflow_path in WORKFLOW_PATHS:
        workflow = workflow_path.read_text(encoding="utf-8")
        for revision in re.findall(r"uses:\s+\S+@([0-9a-f]+)(?:\s|#|$)", workflow):
            assert len(revision) == 40, (
                f"{workflow_path} has a truncated hexadecimal action revision: "
                f"{revision}"
            )
