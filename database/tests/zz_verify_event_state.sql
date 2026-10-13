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
        published_at,
        publish_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf01',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        'org.contextualwisdomlab.ea.object.changed.v1',
        '{}'::jsonb,
        'v1',
        clock_timestamp(),
        'pending'
    );
    RAISE EXCEPTION 'pending outbox row accepted a published timestamp';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

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
        publish_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf02',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        'org.contextualwisdomlab.ea.object.changed.v1',
        '{}'::jsonb,
        'v1',
        'published'
    );
    RAISE EXCEPTION 'published outbox row accepted a missing published timestamp';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

INSERT INTO architecture_core.outbox_event (
    tenant_record_id,
    outbox_event_id,
    aggregate_object_id,
    event_type_code,
    event_payload_json,
    event_schema_version,
    published_at,
    publish_status_code
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf03',
    '0195d145-64e8-7f4f-8a23-a0cc784cb902',
    'org.contextualwisdomlab.ea.object.changed.v1',
    '{}'::jsonb,
    'v1',
    clock_timestamp(),
    'published'
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
        publish_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf04',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        'org.contextualwisdomlab.ea.object.changed.v1',
        '{}'::jsonb,
        'v1',
        'failed'
    );
    RAISE EXCEPTION 'failed outbox row accepted a missing failure code';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

INSERT INTO architecture_core.outbox_event (
    tenant_record_id,
    outbox_event_id,
    aggregate_object_id,
    event_type_code,
    event_payload_json,
    event_schema_version,
    publish_status_code,
    failure_code
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf05',
    '0195d145-64e8-7f4f-8a23-a0cc784cb902',
    'org.contextualwisdomlab.ea.object.changed.v1',
    '{}'::jsonb,
    'v1',
    'failed',
    'broker_unavailable'
);

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
        processed_at,
        processing_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cc001',
        'urn:cwl:tenant_001:ea_core',
        '0195d145-64e8-7f4f-8a23-a0cc784cc101',
        repeat('c', 64),
        'v1',
        clock_timestamp(),
        'received'
    );
    RAISE EXCEPTION 'received projection row accepted a processed timestamp';
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
        processing_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cc002',
        'urn:cwl:tenant_001:ea_core',
        '0195d145-64e8-7f4f-8a23-a0cc784cc102',
        repeat('d', 64),
        'v1',
        'processed'
    );
    RAISE EXCEPTION 'processed projection row accepted a missing processed timestamp';
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
        processed_at,
        processing_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cc003',
        'urn:cwl:tenant_002:ea_core',
        '0195d145-64e8-7f4f-8a23-a0cc784cc103',
        repeat('e', 64),
        'v1',
        clock_timestamp(),
        'processed'
    );
    RAISE EXCEPTION 'projection receipt accepted a foreign tenant source URI';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

INSERT INTO architecture_core.projection_receipt (
    tenant_record_id,
    projection_receipt_id,
    event_source_uri,
    event_identifier,
    payload_sha256,
    schema_version,
    processed_at,
    processing_status_code
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0195d145-64e8-7f4f-8a23-a0cc784cc004',
    'urn:cwl:tenant_001:ea_core',
    '0195d145-64e8-7f4f-8a23-a0cc784cc104',
    repeat('f', 64),
    'v1',
    clock_timestamp(),
    'processed'
);
