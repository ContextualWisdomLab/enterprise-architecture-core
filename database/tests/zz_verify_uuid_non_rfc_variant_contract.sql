\set ON_ERROR_STOP on

-- Exercise the persisted CHECK through the migration-owner connection so a
-- runtime-role privilege boundary cannot mask the UUID invariant under test.
-- Runtime least privilege is verified separately by the purpose-bound port
-- acceptance suite.
RESET ROLE;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
DECLARE
  non_rfc_variant_evidence_id constant uuid :=
      '0196f300-1111-7111-0111-111111111178';
BEGIN
  IF uuid_extract_version(non_rfc_variant_evidence_id) IS NOT NULL THEN
    RAISE EXCEPTION
      'non-RFC UUID fixture unexpectedly reports a version: %',
      uuid_extract_version(non_rfc_variant_evidence_id);
  END IF;

  BEGIN
    INSERT INTO architecture_core.evidence_record (
        tenant_record_id,
        evidence_record_id,
        evidence_uri,
        sha256_digest
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        non_rfc_variant_evidence_id,
        'urn:cwl:tenant_001:ea_core:application_record:0195d145-64e8-7f4f-8a23-a0cc784cb902',
        repeat('a', 64)
    );
    RAISE EXCEPTION 'non-RFC UUID variant evidence identifier unexpectedly succeeded';
  EXCEPTION WHEN check_violation THEN
    IF SQLERRM NOT LIKE '%evidence_record_uuid_version%' THEN
      RAISE;
    END IF;
  END;
END;
$$;
