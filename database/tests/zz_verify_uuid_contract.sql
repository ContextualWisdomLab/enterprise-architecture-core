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
    INSERT INTO architecture_core.evidence_record (
        tenant_record_id,
        evidence_record_id,
        evidence_uri,
        sha256_digest
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '550e8400-e29b-41d4-a716-446655440000',
        'urn:cwl:tenant_001:ea_core:application_record:0195d145-64e8-7f4f-8a23-a0cc784cb902',
        repeat('9', 64)
    );
    RAISE EXCEPTION 'non-UUIDv7 evidence identifier unexpectedly succeeded';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

RESET ROLE;
