\set ON_ERROR_STOP on

-- A Context Assertion receipt must admit every structured JSON media-type form
-- accepted by the released CGC admission contract while still rejecting control
-- characters outside HTTP optional whitespace (SP / HTAB).

INSERT INTO architecture_core.tenant_record (
    tenant_record_id,
    tenant_code,
    tenant_title
) VALUES (
    '0196f301-0000-7000-8000-000000000001',
    'media_tenant',
    'Context Assertion media-type test tenant'
);

SELECT set_config(
    'app.tenant_record_id',
    '0196f301-0000-7000-8000-000000000001',
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
    '0196f301-0000-7000-8000-000000000001',
    '0196f301-2000-7200-8200-000000000001',
    'urn:cwl:media_tenant:quarantine_sandbox_runtime:attestation_provenance:0196f301-2000-7200-8200-000000000001',
    repeat('a', 64),
    'oci://quarantine-sandbox-runtime/attestations/0196f301-2000-7200-8200-000000000001',
    '2026-09-04T00:00:00Z'
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
) VALUES
    (
        '0196f301-0000-7000-8000-000000000001',
        '0196f301-1000-7100-8100-000000000001',
        'urn:cwl:media_tenant:quarantine_sandbox_runtime',
        '0196f301-1000-7100-8100-000000000101',
        repeat('b', 64),
        'context-assertion/v1',
        '2026-09-04T00:00:01Z',
        '2026-09-04T00:00:02Z',
        'processed'
    ),
    (
        '0196f301-0000-7000-8000-000000000001',
        '0196f301-1000-7100-8100-000000000002',
        'urn:cwl:media_tenant:quarantine_sandbox_runtime',
        '0196f301-1000-7100-8100-000000000102',
        repeat('c', 64),
        'context-assertion/v1',
        '2026-09-04T00:00:03Z',
        '2026-09-04T00:00:04Z',
        'processed'
    ),
    (
        '0196f301-0000-7000-8000-000000000001',
        '0196f301-1000-7100-8100-000000000003',
        'urn:cwl:media_tenant:quarantine_sandbox_runtime',
        '0196f301-1000-7100-8100-000000000103',
        repeat('d', 64),
        'context-assertion/v1',
        '2026-09-04T00:00:05Z',
        '2026-09-04T00:00:06Z',
        'processed'
    ),
    (
        '0196f301-0000-7000-8000-000000000001',
        '0196f301-1000-7100-8100-000000000004',
        'urn:cwl:media_tenant:quarantine_sandbox_runtime',
        '0196f301-1000-7100-8100-000000000104',
        repeat('e', 64),
        'context-assertion/v1',
        '2026-09-04T00:00:07Z',
        '2026-09-04T00:00:08Z',
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
    context_profile_version,
    admission_version,
    provenance_evidence_record_id,
    recorded_at
) VALUES (
    '0196f301-0000-7000-8000-000000000001',
    '0196f301-1000-7100-8100-000000000001',
    '1.0',
    'org.contextualwisdomlab.context_graph.assertion.v1',
    'urn:cwl:media_tenant:quarantine_sandbox_runtime:technology_version:0196f301-3000-7300-8300-000000000001',
    '2026-09-03T23:59:59Z',
    'https://schemas.contextualwisdomlab.org/context/context-assertion.v1.schema.json',
    E' \tAPPLICATION/CLOUDEVENTS+JSON ; CHARSET = "UTF-8"\t',
    'context-assertion/v1',
    'context-fabric-admission/v1',
    '0196f301-2000-7200-8200-000000000001',
    '2026-09-04T00:00:09Z'
);

DO $$
DECLARE
  actual_media_type text;
BEGIN
  SELECT transport_media_type
    INTO actual_media_type
    FROM architecture_core.context_assertion_projection_receipt
   WHERE tenant_record_id = '0196f301-0000-7000-8000-000000000001'
     AND projection_receipt_id = '0196f301-1000-7100-8100-000000000001';

  IF actual_media_type IS DISTINCT FROM
        E' \tAPPLICATION/CLOUDEVENTS+JSON ; CHARSET = "UTF-8"\t' THEN
    RAISE EXCEPTION 'Context Assertion receipt did not retain admitted media type';
  END IF;
END;
$$;

DO $$
DECLARE
  receipt_ids uuid[] := ARRAY[
    '0196f301-1000-7100-8100-000000000002'::uuid,
    '0196f301-1000-7100-8100-000000000003'::uuid,
    '0196f301-1000-7100-8100-000000000004'::uuid
  ];
  bad_media_types text[] := ARRAY[
    E'application/cloudevents+json\r',
    E'\vapplication/cloudevents+json',
    E'application/cloudevents+json\f'
  ];
  index_value integer;
  violated_constraint text;
BEGIN
  FOR index_value IN 1..array_length(receipt_ids, 1) LOOP
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
          context_profile_version,
          admission_version,
          provenance_evidence_record_id
      ) VALUES (
          '0196f301-0000-7000-8000-000000000001',
          receipt_ids[index_value],
          '1.0',
          'org.contextualwisdomlab.context_graph.assertion.v1',
          'urn:cwl:media_tenant:quarantine_sandbox_runtime:technology_version:0196f301-3000-7300-8300-000000000001',
          '2026-09-03T23:59:59Z',
          'https://schemas.contextualwisdomlab.org/context/context-assertion.v1.schema.json',
          bad_media_types[index_value],
          'context-assertion/v1',
          'context-fabric-admission/v1',
          '0196f301-2000-7200-8200-000000000001'
      );
      RAISE EXCEPTION 'hostile Context Assertion transport media type was accepted';
    EXCEPTION
      WHEN check_violation THEN
        GET STACKED DIAGNOSTICS violated_constraint = CONSTRAINT_NAME;
        IF violated_constraint IS DISTINCT FROM
              'context_assertion_projection_receipt_media_type' THEN
          RAISE;
        END IF;
    END;
  END LOOP;
END;
$$;
