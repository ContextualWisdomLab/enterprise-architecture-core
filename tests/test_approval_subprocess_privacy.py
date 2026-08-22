"""Privacy regressions for the governed approval subprocess boundary."""

from __future__ import annotations

import json
import subprocess
from typing import Any
from uuid import UUID

from ea_core_foundation.authorization import AuthorizationContext
from ea_core_foundation.service import (
    TargetStateApprovalRequest,
    build_target_state_approval_writer,
)


def test_approval_actor_and_reason_do_not_enter_process_argv() -> None:
    """Human identity and approval rationale must not leak through process listings."""

    captured: list[tuple[list[str], dict[str, str]]] = []

    def runner(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured.append((command, dict(kwargs["env"])))
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(
                {
                    "transformation_history_record_id": (
                        "0196e040-1111-7111-8111-111111111191"
                    ),
                    "transformation_state_code": "approved",
                    "outbox_event_id": "0196e050-1111-7111-8111-111111111191",
                    "decision_request_id": "0196e030-1111-7111-8111-111111111191",
                    "replayed": False,
                    "next_action": "schedule_transformation",
                }
            ),
            stderr="",
        )

    writer = build_target_state_approval_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=runner,
        base_environment={"PATH": "/usr/bin"},
    )
    writer(
        AuthorizationContext(
            tenant_record_id=UUID("018f47b2-905a-7b16-bfd4-7e4f53f10e91"),
            role_code="ea_architecture_approver",
            subject_id="architecture-board-user-123",
            issuer_uri="https://id.example/realms/cwl",
        ),
        TargetStateApprovalRequest.from_values(
            "0196e010-1111-7111-8111-111111111191",
            "0196e030-1111-7111-8111-111111111191",
            "2027-01-15T00:00:00Z",
            "Architecture board approved confidential remediation rationale.",
            "0195d145-64e8-7f4f-8a23-a0cc784cbf10",
        ),
    )

    command, environment = captured[0]
    command_text = " ".join(command)
    assert "architecture-board-user-123" not in command_text
    assert "confidential remediation rationale" not in command_text
    assert environment["EA_APPROVAL_ACTOR_REF"].endswith(
        "#architecture-board-user-123"
    )
    assert environment["EA_APPROVAL_REASON_TEXT"] == (
        "Architecture board approved confidential remediation rationale."
    )
    assert "\\getenv decision_actor_ref EA_APPROVAL_ACTOR_REF" in command
    assert "\\getenv decision_reason_text EA_APPROVAL_REASON_TEXT" in command
