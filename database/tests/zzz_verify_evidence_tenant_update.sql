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
    UPDATE architecture_core.evidence_record
       SET evidence_uri =
           'urn:cwl:tenant_002:semantic_data_portal:data_asset:0195d145-64e8-7f4f-8a23-a0cc784cb912'
     WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND evidence_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cbf12';
    RAISE EXCEPTION 'foreign-tenant evidence URI mutation unexpectedly accepted';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

DO $$
DECLARE
  retained_evidence_uri text;
BEGIN
  SELECT evidence_uri
    INTO retained_evidence_uri
    FROM architecture_core.evidence_record
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND evidence_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cbf12';

  IF retained_evidence_uri IS DISTINCT FROM
      'urn:cwl:tenant_001:semantic_data_portal:data_asset:0195d145-64e8-7f4f-8a23-a0cc784cb912' THEN
    RAISE EXCEPTION 'failed evidence mutation changed persisted provenance: %', retained_evidence_uri;
  END IF;
END;
$$;

RESET ROLE;
