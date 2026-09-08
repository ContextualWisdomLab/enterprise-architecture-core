"""Regression contract for GitHub-hosted runner image selection."""

from pathlib import Path

WORKFLOW_PATHS = (
    Path(".github/workflows/ci.yml"),
    Path(".github/workflows/runtime-readiness.yml"),
    Path(".github/workflows/supply-chain.yml"),
)


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
