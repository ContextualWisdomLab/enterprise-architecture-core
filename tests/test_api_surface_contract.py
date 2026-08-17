"""Regression tests for the implemented API/event specification surface."""


def test_openapi_exposes_only_implemented_process_and_decision_surface(
    openapi_document,
) -> None:
    """Every executable probe, planner read, and approval command is advertised."""

    assert openapi_document["openapi"] == "3.2.0"
    planner_path = "/v1/technology-target-state-plans/{technology_version_id}"
    approval_path = "/v1/architecture-transformations/{architecture_transformation_id}/approval"
    assert set(openapi_document["paths"]) == {
        "/health",
        "/ready",
        planner_path,
        approval_path,
    }
    assert set(openapi_document["paths"]["/health"]) == {"get"}
    assert set(openapi_document["paths"]["/ready"]) == {"get"}
    assert set(openapi_document["paths"][planner_path]) == {"get"}
    assert set(openapi_document["paths"][approval_path]) == {"post"}


def test_openapi_binds_governed_approval_request_receipt_and_role(
    openapi_document,
) -> None:
    """The published command contract matches the executable approval boundary."""

    approval_path = "/v1/architecture-transformations/{architecture_transformation_id}/approval"
    operation = openapi_document["paths"][approval_path]["post"]
    assert operation["operationId"] == "approveTechnologyTargetState"
    assert operation["security"] == [{"keyverseBearer": []}]
    assert operation["requestBody"]["required"] is True
    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    assert request_schema == {"$ref": "#/components/schemas/TargetStateApprovalRequest"}
    assert set(operation["responses"]) == {"200", "201", "400", "401", "403", "503"}
    assert "EA_APPROVAL_ROLES" in openapi_document["x-keyverse-contract"][
        "requiredConfiguration"
    ]

    request = openapi_document["components"]["schemas"]["TargetStateApprovalRequest"]
    assert request["additionalProperties"] is False
    assert request["required"] == [
        "decision_request_id",
        "effective_at",
        "decision_reason_text",
        "evidence_record_id",
    ]
    assert request["properties"]["decision_reason_text"]["maxLength"] == 4096

    receipt = openapi_document["components"]["schemas"]["TargetStateApprovalReceipt"]
    assert receipt["additionalProperties"] is False
    assert receipt["properties"]["transformation_state_code"] == {
        "type": "string",
        "const": "approved",
    }
    assert receipt["properties"]["next_action"] == {
        "type": "string",
        "const": "schedule_transformation",
    }


def test_foundation_asyncapi_tracks_current_stable_minor(asyncapi_document) -> None:
    """The event document uses the accepted current AsyncAPI minor version."""

    assert asyncapi_document["asyncapi"] == "3.1.0"
