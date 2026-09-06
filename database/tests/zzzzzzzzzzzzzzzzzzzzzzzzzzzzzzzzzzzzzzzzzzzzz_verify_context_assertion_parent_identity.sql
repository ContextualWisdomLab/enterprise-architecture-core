\set ON_ERROR_STOP on

-- The generic projection receipt is intentionally reusable across projections.
-- A Context Assertion detail row must nevertheless attach only to a parent that
-- records the exact Context Assertion schema family. Otherwise one receipt can
-- claim a v1 admitted Context Assertion while its immutable parent records an
-- unrelated schema identity.

INSERT INTO architecture_core.tenant_record (
    tenant_record_id,
    tenant_code,
    tenant_title
) VALUES (
    '0196f400-0000-7000-8000-000000000001',
    'receipt_tenant_identity',
    'Context Assertion parent identity test tenant'
);

SELECT set_config(
    'app.tenant_record_id',
    '0196f400-0000-7000-8000-000000000001',
    false
);

INSERT INTO architecture_core.evidence_record (
    tenant_record_id,
    evidence_record_id,
    evidence_uri,
    sha256_digest,
    source_locator,
    recorded_at
) VALUES (
    '0196f400-0000-7000-8000-000000000001',
    '0196f400-2000-7200-8200-000000000001',
    'urn:cwl:receipt_tenant_identity:quarantine_sandbox_runtime:attestation_provenance:0196f400-2000-7200-8200-000000000001',
    repeat('a', 64),
    'oci://quarantine-sandbox-runtime/attestations/0196f400-2000-7200-8200-000000000001',
    '2026-09-07T00:00:00Z'
);

-- The generic parent accepts provider-neutral schema labels by design. This row
-- is therefore valid generic evidence but must not be attachable to the
-- Context-Assertion-specific receipt below.
INSERT INTO architecture_core.projection_receipt (
    tenant_record_id,
    projection_receipt_id,
    event_source_uri,
    event_identifier,
    payload_sha256,
    schema_version,
    received_at,
    processed_at,
    processing_status_code
) VALUES (
    '0196f400-0000-7000-8000-000000000001',
    '0196f400-1000-7100-8100-000000000001',
    'urn:cwl:receipt_tenant_identity:quarantine_sandbox_runtime',
    '0196f400-1000-7100-8100-000000000101',
    repeat('b', 64),
    'unrelated-projection/v9',
    '2026-09-07T00:00:01Z',
    '2026-09-07T00:00:02Z',
    'processed'
);

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.context_assertion_projection_receipt (
        tenant_record_id,
        projection_receipt_id,
        event_specversion,
        event_type,
        event_subject_uri,
        event_time,
        event_dataschema_uri,
        transport_media_type,
        context_schema_version,
        context_profile_id,
        context_profile_version,
        admission_version,
        provenance_evidence_record_id
    ) VALUES (
        '0196f400-0000-7000-8000-000000000001',
        '0196f400-1000-7100-8100-000000000001',
        '1.0',
        'org.contextualwisdomlab.context_graph.assertion.v1',
        'urn:cwl:receipt_tenant_identity:quarantine_sandbox_runtime:technology_version:0196f400-3000-7300-8300-000000000001',
        '2026-09-07T00:00:00Z',
        'https://schemas.contextualwisdomlab.org/context/context-assertion.v1.schema.json',
        'application/cloudevents+json',
        1,
        'urn:cwl:context-contracts:context-assertion-event-semantics:v1',
        1,
        1,
        '0196f400-2000-7200-8200-000000000001'
    );
    RAISE EXCEPTION 'Context Assertion detail accepted mismatched parent schema identity';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;
