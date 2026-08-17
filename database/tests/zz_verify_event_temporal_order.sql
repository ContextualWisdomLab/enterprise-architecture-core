\set ON_ERROR_STOP on

SET ROLE ea_runtime;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.outbox_event (
        tenant_record_id,
        outbox_event_id,
        aggregate_object_id,
        event_type_code,
        event_payload_json,
        event_schema_version,
        recorded_at,
        published_at,
        publish_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf11',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        'org.contextualwisdomlab.ea.object.changed.v1',
        '{}'::jsonb,
        'v1',
        '2026-08-17T05:00:00Z',
        '2026-08-17T04:59:59Z',
        'published'
    );
    RAISE EXCEPTION 'outbox event accepted publication before recording';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
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
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cc011',
        'urn:cwl:tenant_001:ea_core',
        '0195d145-64e8-7f4f-8a23-a0cc784cc111',
        repeat('1', 64),
        'v1',
        '2026-08-17T05:00:00Z',
        '2026-08-17T04:59:59Z',
        'processed'
    );
    RAISE EXCEPTION 'projection receipt accepted processing before receipt';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;
