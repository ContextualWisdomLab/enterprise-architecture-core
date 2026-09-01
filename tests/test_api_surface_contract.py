"""Regression tests for the implemented API/event specification surface."""


def test_openapi_exposes_only_implemented_process_and_decision_surface(
    openapi_document,
) -> None:
    """Every executable probe, planner read, and governed command is advertised."""

    assert openapi_document["openapi"] == "3.2.0"
    planner_path = "/v1/technology-target-state-plans/{technology_version_id}"
    approval_path = (
        "/v1/architecture-transformations/"
        "{architecture_transformation_id}/approval"
    )
    schedule_path = (
        "/v1/architecture-transformations/"
        "{architecture_transformation_id}/schedule"
    )
    start_path = (
        "/v1/architecture-transformations/"
        "{architecture_transformation_id}/start"
    )
    complete_path = (
        "/v1/architecture-transformations/"
        "{architecture_transformation_id}/complete"
    )
    verification_path = (
        "/v1/architecture-transformations/"
        "{architecture_transformation_id}/verification"
    )
    monitoring_path = (
        "/v1/architecture-transformations/"
        "{architecture_transformation_id}/monitoring"
    )
    replan_path = (
        "/v1/architecture-transformations/"
        "{architecture_transformation_id}/replan"
    )
    assert set(openapi_document["paths"]) == {
        "/health",
        "/ready",
        planner_path,
        approval_path,
        schedule_path,
        start_path,
        complete_path,
        verification_path,
        monitoring_path,
        replan_path,
    }
    assert set(openapi_document["paths"]["/health"]) == {"get"}
    assert set(openapi_document["paths"]["/ready"]) == {"get"}
    assert set(openapi_document["paths"][planner_path]) == {"get"}
    assert set(openapi_document["paths"][approval_path]) == {"post"}
    assert set(openapi_document["paths"][schedule_path]) == {"post"}
    assert set(openapi_document["paths"][start_path]) == {"post"}
    assert set(openapi_document["paths"][complete_path]) == {"post"}
    assert set(openapi_document["paths"][verification_path]) == {"post"}
    assert set(openapi_document["paths"][monitoring_path]) == {"get"}
    assert set(openapi_document["paths"][replan_path]) == {"post"}


def test_openapi_binds_governed_approval_request_receipt_and_role(
    openapi_document,
) -> None:
    """The published command contract matches the executable approval boundary."""

    approval_path = (
        "/v1/architecture-transformations/"
        "{architecture_transformation_id}/approval"
    )
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


def test_openapi_binds_governed_schedule_request_receipt_and_role(
    openapi_document,
) -> None:
    """The published contract must include the executable scheduling boundary."""

    schedule_path = (
        "/v1/architecture-transformations/"
        "{architecture_transformation_id}/schedule"
    )
    operation = openapi_document["paths"][schedule_path]["post"]
    assert operation["operationId"] == "scheduleTechnologyTargetState"
    assert operation["security"] == [{"keyverseBearer": []}]
    assert operation["requestBody"]["required"] is True
    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    assert request_schema == {"$ref": "#/components/schemas/TargetStateScheduleRequest"}
    assert set(operation["responses"]) == {"200", "201", "400", "401", "403", "503"}
    assert "EA_SCHEDULE_ROLES" in openapi_document["x-keyverse-contract"][
        "requiredConfiguration"
    ]

    request = openapi_document["components"]["schemas"]["TargetStateScheduleRequest"]
    assert request["additionalProperties"] is False
    assert set(request["required"]) == {
        "decision_request_id",
        "initiative_milestone_id",
        "effective_at",
        "decision_reason_text",
        "evidence_record_id",
    }
    assert request["properties"]["decision_reason_text"]["maxLength"] == 4096

    receipt = openapi_document["components"]["schemas"]["TargetStateScheduleReceipt"]
    assert receipt["additionalProperties"] is False
    assert receipt["properties"]["next_action"] == {
        "type": "string",
        "const": "start_transformation",
    }


def test_openapi_binds_governed_start_request_receipt_and_role(
    openapi_document,
) -> None:
    """The published contract matches the executable transformation-start boundary."""

    start_path = (
        "/v1/architecture-transformations/"
        "{architecture_transformation_id}/start"
    )
    operation = openapi_document["paths"][start_path]["post"]
    assert operation["operationId"] == "startTechnologyTargetState"
    assert operation["security"] == [{"keyverseBearer": []}]
    assert operation["requestBody"]["required"] is True
    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    assert request_schema == {"$ref": "#/components/schemas/TargetStateStartRequest"}
    assert set(operation["responses"]) == {"200", "201", "400", "401", "403", "503"}
    assert "EA_START_ROLES" in openapi_document["x-keyverse-contract"][
        "requiredConfiguration"
    ]

    request = openapi_document["components"]["schemas"]["TargetStateStartRequest"]
    assert request["additionalProperties"] is False
    assert request["required"] == [
        "decision_request_id",
        "effective_at",
        "decision_reason_text",
        "evidence_record_id",
    ]
    receipt = openapi_document["components"]["schemas"]["TargetStateStartReceipt"]
    assert receipt["additionalProperties"] is False
    assert receipt["properties"]["transformation_state_code"] == {
        "type": "string",
        "const": "started",
    }
    assert receipt["properties"]["next_action"] == {
        "type": "string",
        "const": "monitor_transformation",
    }


def test_openapi_binds_governed_completion_request_receipt_and_role(
    openapi_document,
) -> None:
    """The published contract matches the purpose-bound completion boundary."""

    complete_path = (
        "/v1/architecture-transformations/"
        "{architecture_transformation_id}/complete"
    )
    operation = openapi_document["paths"][complete_path]["post"]
    assert operation["operationId"] == "completeTechnologyTargetState"
    assert operation["security"] == [{"keyverseBearer": []}]
    assert operation["requestBody"]["required"] is True
    request_schema = operation["requestBody"]["content"]["application/json"]["schema"]
    assert request_schema == {"$ref": "#/components/schemas/TargetStateCompleteRequest"}
    assert set(operation["responses"]) == {"200", "201", "400", "401", "403", "503"}
    assert "EA_COMPLETE_ROLES" in openapi_document["x-keyverse-contract"][
        "requiredConfiguration"
    ]

    request = openapi_document["components"]["schemas"]["TargetStateCompleteRequest"]
    assert request["additionalProperties"] is False
    assert request["required"] == [
        "decision_request_id",
        "effective_at",
        "decision_reason_text",
        "evidence_record_id",
    ]
    receipt = openapi_document["components"]["schemas"]["TargetStateCompleteReceipt"]
    assert receipt["additionalProperties"] is False
    assert receipt["properties"]["transformation_state_code"] == {
        "type": "string",
        "const": "completed",
    }
    assert receipt["properties"]["next_action"] == {
        "type": "string",
        "const": "verify_target_state",
    }


def test_openapi_binds_governed_replan_request_receipt_and_role(
    openapi_document,
) -> None:
    """The published contract closes the gap-detected target-state decision loop."""

    replan_path = (
        "/v1/architecture-transformations/"
        "{architecture_transformation_id}/replan"
    )
    operation = openapi_document["paths"][replan_path]["post"]
    assert operation["operationId"] == "replanTechnologyTargetState"
    assert operation["security"] == [{"keyverseBearer": []}]
    assert operation["requestBody"]["required"] is True
    assert operation["requestBody"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/TargetStateReplanRequest"
    }
    assert set(operation["responses"]) == {"200", "201", "400", "401", "403", "503"}
    assert "EA_REPLAN_ROLES" in openapi_document["x-keyverse-contract"][
        "requiredConfiguration"
    ]

    request = openapi_document["components"]["schemas"]["TargetStateReplanRequest"]
    assert request["additionalProperties"] is False
    assert set(request["required"]) == {
        "decision_request_id",
        "replacement_architecture_transformation_id",
        "architecture_scenario_id",
        "remediation_initiative_id",
        "transformation_code",
        "transformation_title",
        "transformation_description",
        "effective_at",
        "decision_reason_text",
        "evidence_record_id",
    }
    receipt = openapi_document["components"]["schemas"]["TargetStateReplanReceipt"]
    assert receipt["additionalProperties"] is False
    assert receipt["properties"]["next_action"] == {
        "type": "string",
        "const": "approve_target_state",
    }


def test_asyncapi_publishes_transformation_schedule_event(asyncapi_document) -> None:
    """Scheduling's transactional outbox event must be in the event contract."""

    channel = asyncapi_document["channels"]["transformationScheduleEvents"]
    assert channel["address"] == (
        "org.contextualwisdomlab.ea.transformation.scheduled.v1"
    )
    operation = asyncapi_document["operations"]["publishTransformationScheduled"]
    assert operation["action"] == "send"
    message = asyncapi_document["components"]["messages"]["TransformationScheduled"]
    event_type = message["payload"]["schema"]["allOf"][1]["properties"]["type"]
    assert event_type["const"] == (
        "org.contextualwisdomlab.ea.transformation.scheduled.v1"
    )


def test_asyncapi_publishes_transformation_started_event(asyncapi_document) -> None:
    """Starting's transactional outbox event must be in the event contract."""

    channel = asyncapi_document["channels"]["transformationStartEvents"]
    assert channel["address"] == "org.contextualwisdomlab.ea.transformation.started.v1"
    operation = asyncapi_document["operations"]["publishTransformationStarted"]
    assert operation["action"] == "send"
    message = asyncapi_document["components"]["messages"]["TransformationStarted"]
    event_type = message["payload"]["schema"]["allOf"][1]["properties"]["type"]
    assert event_type["const"] == "org.contextualwisdomlab.ea.transformation.started.v1"


def test_asyncapi_publishes_transformation_completed_event(asyncapi_document) -> None:
    """Completion's transactional outbox event must be in the event contract."""

    channel = asyncapi_document["channels"]["transformationCompleteEvents"]
    assert channel["address"] == (
        "org.contextualwisdomlab.ea.transformation.completed.v1"
    )
    operation = asyncapi_document["operations"]["publishTransformationCompleted"]
    assert operation["action"] == "send"
    message = asyncapi_document["components"]["messages"]["TransformationCompleted"]
    event_type = message["payload"]["schema"]["allOf"][1]["properties"]["type"]
    assert event_type["const"] == (
        "org.contextualwisdomlab.ea.transformation.completed.v1"
    )


def test_asyncapi_publishes_transformation_replanned_event(asyncapi_document) -> None:
    """Replanning's transactional outbox event must be discoverable by consumers."""

    channel = asyncapi_document["channels"]["transformationReplanEvents"]
    assert channel["address"] == (
        "org.contextualwisdomlab.ea.transformation.replanned.v1"
    )
    operation = asyncapi_document["operations"]["publishTransformationReplanned"]
    assert operation["action"] == "send"
    message = asyncapi_document["components"]["messages"]["TransformationReplanned"]
    event_type = message["payload"]["schema"]["allOf"][1]["properties"]["type"]
    assert event_type["const"] == (
        "org.contextualwisdomlab.ea.transformation.replanned.v1"
    )


def test_foundation_asyncapi_tracks_current_stable_minor(asyncapi_document) -> None:
    """The event document uses the accepted current AsyncAPI minor version."""

    assert asyncapi_document["asyncapi"] == "3.1.0"
