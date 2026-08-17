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
    INSERT INTO architecture_core.business_capability (
        tenant_record_id,
        architecture_object_id,
        capability_code,
        capability_level
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        'invalid_application_as_capability',
        1
    );
    RAISE EXCEPTION 'typed extension accepted the wrong object type';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.architecture_object
       SET object_type_id = '0195d145-64e8-7f4f-8a23-a0cc784cb802'
     WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND architecture_object_id = '0195d145-64e8-7f4f-8a23-a0cc784cb901';
    RAISE EXCEPTION 'referenced object type unexpectedly changed';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.tenant_record
       SET tenant_code = 'tenant_renamed'
     WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711';
    RAISE EXCEPTION 'referenced tenant code unexpectedly changed';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.object_type
       SET object_type_code = 'capability_renamed'
     WHERE object_type_id = '0195d145-64e8-7f4f-8a23-a0cc784cb801';
    RAISE EXCEPTION 'referenced object type code unexpectedly changed';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

INSERT INTO architecture_core.object_revision (
    tenant_record_id,
    object_revision_id,
    architecture_object_id,
    revision_number,
    object_title,
    valid_from,
    valid_to,
    truth_status_code
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0195d145-64e8-7f4f-8a23-a0cc784cba12',
    '0195d145-64e8-7f4f-8a23-a0cc784cb902',
    2,
    'Proposed Overlap',
    '2026-06-01T00:00:00Z',
    '2026-08-01T00:00:00Z',
    'proposed'
);

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.object_revision (
        tenant_record_id,
        object_revision_id,
        architecture_object_id,
        revision_number,
        object_title,
        valid_from,
        truth_status_code,
        evidence_record_id
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cba13',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        3,
        'Second Authoritative Overlap',
        '2026-06-15T00:00:00Z',
        'authoritative',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    );
    RAISE EXCEPTION 'second authoritative revision unexpectedly succeeded';
  EXCEPTION
    WHEN exclusion_violation THEN NULL;
  END;
END;
$$;

INSERT INTO architecture_core.architecture_relation (
    tenant_record_id,
    architecture_relation_id,
    relation_type_id,
    source_object_id,
    target_object_id,
    valid_from,
    valid_to,
    truth_status_code
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0195d145-64e8-7f4f-8a23-a0cc784cbb12',
    '0195d145-64e8-7f4f-8a23-a0cc784cb811',
    '0195d145-64e8-7f4f-8a23-a0cc784cb902',
    '0195d145-64e8-7f4f-8a23-a0cc784cb901',
    '2026-06-01T00:00:00Z',
    '2026-08-01T00:00:00Z',
    'proposed'
);

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.architecture_relation (
        tenant_record_id,
        architecture_relation_id,
        relation_type_id,
        source_object_id,
        target_object_id,
        valid_from,
        truth_status_code,
        evidence_record_id
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cbb13',
        '0195d145-64e8-7f4f-8a23-a0cc784cb811',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '0195d145-64e8-7f4f-8a23-a0cc784cb901',
        '2026-06-15T00:00:00Z',
        'authoritative',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    );
    RAISE EXCEPTION 'second authoritative relation unexpectedly succeeded';
  EXCEPTION
    WHEN exclusion_violation THEN NULL;
  END;
END;
$$;

RESET ROLE;
