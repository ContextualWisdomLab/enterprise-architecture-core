"""Regression coverage for binding approval receipts to the exact command."""

import json
import subprocess
from uuid import UUID

import pytest

from ea_core_foundation.authorization import AuthorizationContext
from ea_core_foundation.service import (
    PlannerExecutionError,
    TargetStateApprovalRequest,
    build_target_state_approval_writer,
)

_TENANT_ID = "018f47b2-905a-7b16-bfd4-7e4f53f10e91"
_TRANSFORMATION_ID = "0196e010-1111-7111-8111-111111111191"
_DECISION_REQUEST_ID = "0196e030-1111-7111-8111-111111111191"
_OTHER_DECISION_REQUEST_ID = "0196e030-2222-7222-8222-222222222292"
_EVIDENCE_ID = "0195d145-64e8-7f4f-8a23-a0cc784cbf10"


def test_approval_writer_rejects_receipt_for_another_decision_request() -> None:
    """A successful DB call cannot acknowledge a different idempotency command key."""

    def runner(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        del kwargs
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
                    "decision_request_id": _OTHER_DECISION_REQUEST_ID,
                    "replayed": False,
                    "next_action": "schedule_transformation",
                }
            ),
            stderr="",
        )

    writer = build_target_state_approval_writer(
        "postgresql://ea_runtime@db.example/ea_core",
        runner=runner,
        base_environment={},
    )
    context = AuthorizationContext(
        tenant_record_id=UUID(_TENANT_ID),
        role_code="ea_architecture_approver",
        subject_id="architecture-board-user-123",
        issuer_uri="https://id.example/realms/cwl",
    )
    request = TargetStateApprovalRequest.from_values(
        _TRANSFORMATION_ID,
        _DECISION_REQUEST_ID,
        "2027-01-15T00:00:00Z",
        "Architecture board approved the reviewed target state.",
        _EVIDENCE_ID,
    )

    with pytest.raises(PlannerExecutionError, match="invalid decision receipt"):
        writer(context, request)
