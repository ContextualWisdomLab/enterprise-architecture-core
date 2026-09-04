\set ON_ERROR_STOP on

-- An admitted Context Assertion must remain attributable to the exact CloudEvent
-- and compatibility contract that created the EA-side projection receipt.

INSERT INTO architecture_core.tenant_record (
    tenant_record_id,
    tenant_code,
    tenant_title
) VALUES (
    '0196f300-0000-7000-8000-000000000001',
    'receipt_tenant',
    'Context Assertion receipt test tenant'
);

SELECT set_config(
    'app.tenant_record_id',
    '0196f300-0000-7000-8000-000000000001',
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
    '0196f300-0000-7000-8000-000000000001',
    '0196f300-2000-7200-8200-000000000001',
    'urn:cwl:receipt_tenant:quarantine_sandbox_runtime:attestation_provenance:0196f300-2000-7200-8200-000000000001',
    repeat('d', 64),
    'oci://quarantine-sandbox-runtime/attestations/0196f300-2000-7200-8200-000000000001',
    '2026-09-03T09:00:00Z'
);

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
    '0196f300-0000-7000-8000-000000000001',
    '0196f300-1000-7100-8100-000000000001',
    'urn:cwl:receipt_tenant:quarantine_sandbox_runtime',
    '0196f300-1000-7100-8100-000000000101',
    repeat('e', 64),
    'context-assertion/v1',
    '2026-09-03T09:00:01Z',
    '2026-09-03T09:00:02Z',
    'processed'
);

INSERT INTO architecture_core.context_assertion_projection_receipt (
    tenant_record_id,
    projection_receipt_id,
    event_specversion,
    event_type,
    event_subject_uri,
    event_time,
    event_dataschema_uri,
    transport_media_type,
    context_profile_id,
    context_profile_version,
    admission_version,
    provenance_evidence_record_id,
    recorded_at
) VALUES (
    '0196f300-0000-7000-8000-000000000001',
    '0196f300-1000-7100-8100-000000000001',
    '1.0',
    'org.contextualwisdomlab.context_graph.assertion.v1',
    'urn:cwl:receipt_tenant:quarantine_sandbox_runtime:technology_version:0196f300-3000-7300-8300-000000000001',
    '2026-09-03T08:59:59Z',
    'https://schemas.contextualwisdomlab.org/context/context-assertion.v1.schema.json',
    'application/cloudevents+json',
    'urn:cwl:context-contracts:context-assertion-event-semantics:v1',
    1,
    1,
    '0196f300-2000-7200-8200-000000000001',
    '2026-09-03T09:00:03Z'
);

DO $$
DECLARE
  actual_source text;
  actual_event_identifier text;
  actual_specversion text;
  actual_event_type text;
  actual_subject text;
  actual_dataschema text;
  actual_profile_id text;
  actual_profile_version integer;
  actual_admission integer;
  actual_provenance uuid;
  rls_enabled boolean;
  rls_forced boolean;
BEGIN
  SELECT
      base.event_source_uri,
      base.event_identifier,
      detail.event_specversion,
      detail.event_type,
      detail.event_subject_uri,
      detail.event_dataschema_uri,
      detail.context_profile_id,
      detail.context_profile_version,
      detail.admission_version,
      detail.provenance_evidence_record_id
    INTO
      actual_source,
      actual_event_identifier,
      actual_specversion,
      actual_event_type,
      actual_subject,
      actual_dataschema,
      actual_profile_id,
      actual_profile_version,
      actual_admission,
      actual_provenance
    FROM architecture_core.projection_receipt AS base
    JOIN architecture_core.context_assertion_projection_receipt AS detail
      USING (tenant_record_id, projection_receipt_id)
   WHERE base.tenant_record_id =
         '0196f300-0000-7000-8000-000000000001'
     AND base.projection_receipt_id =
         '0196f300-0000-7000-8000-000000000001'::uuid +
         '00000000-1000-0100-0100-000000000000'::uuid;

  IF actual_source IS DISTINCT FROM
        'urn:cwl:receipt_tenant:quarantine_sandbox_runtime'
     OR actual_event_identifier IS DISTINCT FROM
        '0196f300-1000-7100-8100-000000000101'
     OR actual_specversion IS DISTINCT FROM '1.0'
     OR actual_event_type IS DISTINCT FROM
        'org.contextualwisdomlab.context_graph.assertion.v1'
     OR actual_subject IS DISTINCT FROM
        'urn:cwl:receipt_tenant:quarantine_sandbox_runtime:technology_version:0196f300-3000-7301-8300-000000000001'
     OR actual_dataschema IS DISTINCT FROM
        'https://schemas.contextualwisdomlab.org/context/context-assertion.v1.schema.json'
     OR actual_profile_id IS DISTINCT FROM
        'urn:cwl:context-contracts:context-assertion-event-semantics:v1'
     OR actual_profile_version IS DISTINCT FROM 1
     OR actual_admission IS DISTINCT FROM 1
     OR actual_provenance IS DISTINCT FROM
        '0196f300-2000-7200-8200-000000000001'::uuid THEN
    RERAISE;
  END IF;

  SELECT relrowsecurity, relforcerowsecurity
    INTO rls_enabled, rls_forced
    FROM pg_class
   WHERE oid = 'architecture_core.context_assertion_projection_receipt'::regclass;

  IF rls_enabled IS DISTINCT FROM true OR rls_forced IS DISTINCT FROM true THEN
    RAISE EXCEPTION 'Context Assertion projection receipt must use forced RLS';
  END IF;
END;
$$;

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
    '0196f300-0000-7000-8000-000000000001',
    '0196f300-1000-7100-8100-000000000002',
    'urn:cwl:receipt_tenant:quarantine_sandbox_runtime',
    '0196f300-1000-7100-8100-000000000102',
    repeat('f', 64),
    'context-assertion/v1',
    '2026-09-03T09:01:01Z',
    '2026-09-03T09:01:02Z',
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
        context_profile_id,
        context_profile_version,
        admission_version,
        provenance_evidence_record_id
    ) VALUES (
        '0196f300-0000-7000-8000-000000000001',
        '0196f300-1000-7100-8100-000000000002',
        '0.3',
        'org.contextualwisdomlab.context_graph.assertion.v1',
        'urn:cwl:receipt_tenant:quarantine_sandbox_runtime:technology_version:0196f300-3000-7300-8300-000000000001',
        '2026-09-03T09:00:59Z',
        'https://schemas.contextualwisdomlab.org/context/context-assertion.v1.schema.json',
        'application/cloudevents+json',
        'urn:cwl:context-contracts:context_assertion_event_semantics:v1',
        1,
        1,
        '0196f300-2000-7200-8200-000000000001'
    );
    RAISE EXCEPTION 'non-1.0 CloudEvent specversion was accepted';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.context_assertion_projection_receipt
       SET admission_version = 2
     WHERE tenant_record_id =
           '0196f300-0000-7000-8000-000000000001'
       AND projection_receipt_id =
           '0196f300-1000-7100-8100-000000000001';
    RAISE EXCEPTION 'Context Assertion admission identity was rewritten';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    DELETE FROM architecture_core.context_assertion_projection_receipt
     WHERE tenant_record_id =
           '0196f300-0000-7000-8000-000000000001'
       AND projection_receipt_id =
           '0196f300-1000-7100-8100-000000000001';
    RAISE EXCEPTION 'Context Assertion projection receipt was hard-deleted';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;
