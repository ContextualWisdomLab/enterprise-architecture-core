\set ON_ERROR_STOP on

SET ROLE ea_runtime;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

INSERT INTO architecture_core.evidence_record (
    tenant_record_id,
    evidence_record_id,
    evidence_uri,
    sha256_digest,
    source_locator
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf11',
    'urn:cwl:tenant_001:ea_core:application_record:0195d145-64e8-7f4f-8a23-a0cc784cb902',
    repeat('c', 64),
    'semantic-data-portal:evidence-123'
);

DO $$
DECLARE
  invalid_evidence_uri text;
  probe_index integer := 0;
  probe_id uuid;
BEGIN
  FOREACH invalid_evidence_uri IN ARRAY ARRAY[
      'https://user:secret@example.com/evidence?token=secret',
      '/var/lib/private',
      'urn:cwl:tenant_001:ea_core',
      'not a uri'
  ]
  LOOP
    probe_index := probe_index + 1;
    probe_id := format(
        '0195d145-64e8-7f4f-8a23-a0cc784cbf%02s',
        11 + probe_index
    )::uuid;
    BEGIN
      INSERT INTO architecture_core.evidence_record (
          tenant_record_id,
          evidence_record_id,
          evidence_uri,
          sha256_digest
      ) VALUES (
          '0195d145-64e8-7f4f-8a23-a0cc784cb711',
          probe_id,
          invalid_evidence_uri,
          repeat('d', 64)
      );
      RAISE EXCEPTION 'invalid evidence URI unexpectedly accepted: %', invalid_evidence_uri;
    EXCEPTION
      WHEN check_violation THEN NULL;
    END;
  END LOOP;
END;
$$;

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.evidence_record (
        tenant_record_id,
        evidence_record_id,
        evidence_uri,
        sha256_digest,
        source_locator
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf20',
        'urn:cwl:tenant_001:ea_core:application_record:0195d145-64e8-7f4f-8a23-a0cc784cb902',
        repeat('e', 64),
        ''
    );
    RAISE EXCEPTION 'empty source locator unexpectedly accepted';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.evidence_record (
        tenant_record_id,
        evidence_record_id,
        evidence_uri,
        sha256_digest,
        source_locator
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf21',
        'urn:cwl:tenant_001:ea_core:application_record:0195d145-64e8-7f4f-8a23-a0cc784cb902',
        repeat('f', 64),
        repeat('x', 2049)
    );
    RAISE EXCEPTION 'oversized source locator unexpectedly accepted';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

RESET ROLE;
