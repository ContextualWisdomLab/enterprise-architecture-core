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

INSERT INTO architecture_core.evidence_record (
    tenant_record_id,
    evidence_record_id,
    evidence_uri,
    sha256_digest,
    source_locator
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf12',
    'urn:cwl:tenant_001:semantic_data_portal:data_asset:0195d145-64e8-7f4f-8a23-a0cc784cb912',
    repeat('b', 64),
    'catalog:asset-912'
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
        '0195d145-64e8-7f4f-8a23-a0cc784cbf13',
        'urn:cwl:tenant_002:semantic_data_portal:data_asset:0195d145-64e8-7f4f-8a23-a0cc784cb913',
        repeat('9', 64)
    );
    RAISE EXCEPTION 'foreign-tenant evidence URI unexpectedly accepted';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

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
        13 + probe_index
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

DO $$
DECLARE
  required_status text;
  probe_index integer := 0;
BEGIN
  FOREACH required_status IN ARRAY ARRAY['authoritative', 'observed']
  LOOP
    probe_index := probe_index + 1;
    BEGIN
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
          format('0195d145-64e8-7f4f-8a23-a0cc784cbf3%s', probe_index)::uuid,
          '0195d145-64e8-7f4f-8a23-a0cc784cb902',
          30 + probe_index,
          'Evidence-required revision',
          format('203%s-01-01T00:00:00Z', probe_index)::timestamptz,
          format('203%s-06-01T00:00:00Z', probe_index)::timestamptz,
          required_status
      );
      RAISE EXCEPTION '% object revision without evidence unexpectedly accepted', required_status;
    EXCEPTION
      WHEN check_violation THEN NULL;
    END;
  END LOOP;
END;
$$;

DO $$
DECLARE
  required_status text;
  probe_index integer := 0;
BEGIN
  FOREACH required_status IN ARRAY ARRAY['authoritative', 'observed']
  LOOP
    probe_index := probe_index + 1;
    BEGIN
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
          format('0195d145-64e8-7f4f-8a23-a0cc784cbf4%s', probe_index)::uuid,
          '0195d145-64e8-7f4f-8a23-a0cc784cb811',
          '0195d145-64e8-7f4f-8a23-a0cc784cb902',
          '0195d145-64e8-7f4f-8a23-a0cc784cb901',
          format('204%s-01-01T00:00:00Z', probe_index)::timestamptz,
          format('204%s-06-01T00:00:00Z', probe_index)::timestamptz,
          required_status
      );
      RAISE EXCEPTION '% architecture relation without evidence unexpectedly accepted', required_status;
    EXCEPTION
      WHEN check_violation THEN NULL;
    END;
  END LOOP;
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
    '0195d145-64e8-7f4f-8a23-a0cc784cbf50',
    '0195d145-64e8-7f4f-8a23-a0cc784cb902',
    50,
    'Proposed evidence-optional revision',
    '2050-01-01T00:00:00Z',
    '2050-06-01T00:00:00Z',
    'proposed'
);

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
    '0195d145-64e8-7f4f-8a23-a0cc784cbf51',
    '0195d145-64e8-7f4f-8a23-a0cc784cb811',
    '0195d145-64e8-7f4f-8a23-a0cc784cb902',
    '0195d145-64e8-7f4f-8a23-a0cc784cb901',
    '2051-01-01T00:00:00Z',
    '2051-06-01T00:00:00Z',
    'inferred'
);

RESET ROLE;
