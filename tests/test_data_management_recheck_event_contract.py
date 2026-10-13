"""Contract regression for assessment-recheck transactional outbox publication."""


def test_assessment_recheck_event_is_explicit_and_privacy_minimized(
    asyncapi_document,
) -> None:
    """The reassessment event exposes only the receipt and causal buyer fields."""

    channel = asyncapi_document["channels"]["dataManagementAssessmentRecheckEvents"]
    assert channel["address"] == (
        "org.contextualwisdomlab.ea.data_management.assessment_recheck_requested.v1"
    )
    assert channel["messages"] == {
        "DataManagementAssessmentRecheckRequested": {
            "$ref": "#/components/messages/DataManagementAssessmentRecheckRequested"
        }
    }

    operation = asyncapi_document["operations"][
        "publishDataManagementAssessmentRecheckRequested"
    ]
    assert operation["action"] == "send"
    assert operation["channel"] == {
        "$ref": "#/channels/dataManagementAssessmentRecheckEvents"
    }
    assert operation["messages"] == [
        {
            "$ref": (
                "#/channels/dataManagementAssessmentRecheckEvents/messages/"
                "DataManagementAssessmentRecheckRequested"
            )
        }
    ]

    message = asyncapi_document["components"]["messages"][
        "DataManagementAssessmentRecheckRequested"
    ]
    event_schema = message["payload"]["schema"]["allOf"][1]
    assert event_schema["required"] == ["type", "data"]
    assert event_schema["properties"]["type"] == {
        "const": (
            "org.contextualwisdomlab.ea.data_management."
            "assessment_recheck_requested.v1"
        )
    }
    data_schema = event_schema["properties"]["data"]
    expected_fields = {
        "assessment_recheck_request_id",
        "data_management_assessment_projection_id",
        "trigger_evidence_acceptance_id",
        "assessment_result_uri",
        "next_action",
    }
    assert data_schema["type"] == "object"
    assert set(data_schema["required"]) == expected_fields
    assert set(data_schema["properties"]) == expected_fields
    assert data_schema["additionalProperties"] is False
    assert data_schema["properties"]["next_action"] == {
        "const": "await_assessment_recheck"
    }
