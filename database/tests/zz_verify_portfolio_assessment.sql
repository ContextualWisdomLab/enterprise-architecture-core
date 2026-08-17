\set ON_ERROR_STOP on

-- Buyer acceptance for versioned portfolio assessment. The first branch commit
-- added this acceptance before migration 0010, producing a real hosted RED run
-- before the implementation existed.

DO $$
DECLARE
  missing_table_count integer;
BEGIN
  SELECT count(*)
    INTO missing_table_count
    FROM (VALUES
      ('assessment_framework'),
      ('assessment_scale'),
      ('assessment_scale_value'),
      ('assessment_dimension'),
      ('assessment_cycle'),
      ('object_assessment')
    ) AS required_table(table_name)
   WHERE to_regclass('architecture_core.' || required_table.table_name) IS NULL;

  IF missing_table_count <> 0 THEN
    RAISE EXCEPTION 'portfolio assessment tables missing: %', missing_table_count;
  END IF;
END;
$$;

INSERT INTO architecture_core.assessment_framework (
    tenant_record_id,
    assessment_framework_id,
    framework_code,
    framework_title,
    framework_version_label,
    valid_from
) VALUES
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196a001-1111-7111-8111-111111111111',
        'technology_risk',
        'Technology Risk',
        '2026.1',
        '2026-01-01T00:00:00Z'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb712',
        '0196a001-1111-7111-8111-111111111112',
        'technology_risk',
        'Technology Risk',
        '2026.1',
        '2026-01-01T00:00:00Z'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196a001-1111-7111-8111-111111111113',
        'business_fit',
        'Business Fit',
        '2026.1',
        '2026-01-01T00:00:00Z'
    );

INSERT INTO architecture_core.assessment_scale (
    tenant_record_id,
    assessment_scale_id,
    assessment_framework_id,
    scale_code,
    scale_title
) VALUES
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196a002-1111-7111-8111-111111111111',
        '0196a001-1111-7111-8111-111111111111',
        'risk_five_point',
        'Five-point risk scale'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196a002-1111-7111-8111-111111111112',
        '0196a001-1111-7111-8111-111111111111',
        'confidence_three_point',
        'Three-point confidence scale'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196a002-1111-7111-8111-111111111113',
        '0196a001-1111-7111-8111-111111111113',
        'fit_five_point',
        'Five-point fit scale'
    );

INSERT INTO architecture_core.assessment_scale_value (
    tenant_record_id,
    scale_value_id,
    assessment_scale_id,
    score_value,
    score_label,
    ordinal_rank
) VALUES
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196a003-1111-7111-8111-111111111111',
        '0196a002-1111-7111-8111-111111111111',
        5,
        'Critical',
        5
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196a003-1111-7111-8111-111111111112',
        '0196a002-1111-7111-8111-111111111112',
        3,
        'High confidence',
        3
    );

INSERT INTO architecture_core.assessment_dimension (
    tenant_record_id,
    assessment_dimension_id,
    assessment_scale_id,
    dimension_code,
    dimension_title
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196a004-1111-7111-8111-111111111111',
    '0196a002-1111-7111-8111-111111111111',
    'support_risk',
    'Vendor support risk'
);

INSERT INTO architecture_core.assessment_cycle (
    tenant_record_id,
    assessment_cycle_id,
    assessment_framework_id,
    cycle_code,
    cycle_title,
    valid_from,
    valid_to
) VALUES
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196a005-1111-7111-8111-111111111111',
        '0196a001-1111-7111-8111-111111111111',
        'fy2026_q3',
        'FY2026 Q3',
        '2026-07-01T00:00:00Z',
        '2026-10-01T00:00:00Z'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196a005-1111-7111-8111-111111111112',
        '0196a001-1111-7111-8111-111111111113',
        'fy2026_q3',
        'FY2026 Q3',
        '2026-07-01T00:00:00Z',
        '2026-10-01T00:00:00Z'
    );

INSERT INTO architecture_core.evidence_record (
    tenant_record_id,
    evidence_record_id,
    evidence_uri,
    sha256_digest,
    source_locator
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196a006-1111-7111-8111-111111111111',
    'urn:cwl:tenant_001:ea_core:application_record:0195d145-64e8-7f4f-8a23-a0cc784cb902',
    repeat('a', 64),
    'assessment://technology-risk/fy2026-q3'
)
ON CONFLICT DO NOTHING;

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.object_assessment (
        tenant_record_id,
        object_assessment_id,
        architecture_object_id,
        assessment_dimension_id,
        assessment_cycle_id,
        scale_value_id,
        valid_from,
        truth_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196a007-1111-7111-8111-111111111111',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '0196a004-1111-7111-8111-111111111111',
        '0196a005-1111-7111-8111-111111111111',
        '0196a003-1111-7111-8111-111111111111',
        '2026-07-01T00:00:00Z',
        'authoritative'
    );
    RAISE EXCEPTION 'authoritative assessment without evidence was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.object_assessment (
        tenant_record_id,
        object_assessment_id,
        architecture_object_id,
        assessment_dimension_id,
        assessment_cycle_id,
        scale_value_id,
        valid_from,
        truth_status_code,
        evidence_record_id
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196a007-1111-7111-8111-111111111112',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '0196a004-1111-7111-8111-111111111111',
        '0196a005-1111-7111-8111-111111111111',
        '0196a003-1111-7111-8111-111111111112',
        '2026-07-01T00:00:00Z',
        'authoritative',
        '0196a006-1111-7111-8111-111111111111'
    );
    RAISE EXCEPTION 'assessment accepted a value from the wrong scale';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.object_assessment (
        tenant_record_id,
        object_assessment_id,
        architecture_object_id,
        assessment_dimension_id,
        assessment_cycle_id,
        scale_value_id,
        valid_from,
        truth_status_code,
        evidence_record_id
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196a007-1111-7111-8111-111111111113',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '0196a004-1111-7111-8111-111111111111',
        '0196a005-1111-7111-8111-111111111112',
        '0196a003-1111-7111-8111-111111111111',
        '2026-07-01T00:00:00Z',
        'authoritative',
        '0196a006-1111-7111-8111-111111111111'
    );
    RAISE EXCEPTION 'assessment accepted a cycle from another framework';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

INSERT INTO architecture_core.object_assessment (
    tenant_record_id,
    object_assessment_id,
    architecture_object_id,
    assessment_dimension_id,
    assessment_cycle_id,
    scale_value_id,
    valid_from,
    valid_to,
    truth_status_code,
    evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196a007-1111-7111-8111-111111111114',
    '0195d145-64e8-7f4f-8a23-a0cc784cb902',
    '0196a004-1111-7111-8111-111111111111',
    '0196a005-1111-7111-8111-111111111111',
    '0196a003-1111-7111-8111-111111111111',
    '2026-07-01T00:00:00Z',
    '2026-10-01T00:00:00Z',
    'authoritative',
    '0196a006-1111-7111-8111-111111111111'
);

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.object_assessment (
        tenant_record_id,
        object_assessment_id,
        architecture_object_id,
        assessment_dimension_id,
        assessment_cycle_id,
        scale_value_id,
        valid_from,
        valid_to,
        truth_status_code,
        evidence_record_id
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196a007-1111-7111-8111-111111111115',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '0196a004-1111-7111-8111-111111111111',
        '0196a005-1111-7111-8111-111111111111',
        '0196a003-1111-7111-8111-111111111111',
        '2026-08-01T00:00:00Z',
        '2026-09-01T00:00:00Z',
        'authoritative',
        '0196a006-1111-7111-8111-111111111111'
    );
    RAISE EXCEPTION 'overlapping authoritative assessment was accepted';
  EXCEPTION WHEN exclusion_violation THEN
    NULL;
  END;
END;
$$;

-- A competing inferred assessment remains reviewable and cannot silently replace
-- the authoritative fact.
INSERT INTO architecture_core.object_assessment (
    tenant_record_id,
    object_assessment_id,
    architecture_object_id,
    assessment_dimension_id,
    assessment_cycle_id,
    scale_value_id,
    valid_from,
    valid_to,
    truth_status_code
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196a007-1111-7111-8111-111111111116',
    '0195d145-64e8-7f4f-8a23-a0cc784cb902',
    '0196a004-1111-7111-8111-111111111111',
    '0196a005-1111-7111-8111-111111111111',
    '0196a003-1111-7111-8111-111111111111',
    '2026-08-01T00:00:00Z',
    '2026-09-01T00:00:00Z',
    'inferred'
);

-- Once an assessment meaning has been used, mutating any of its normalized
-- determinants would retrospectively rewrite historical decisions. Corrections
-- must supersede rows and create new definition/assessment facts instead.
DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.assessment_framework
       SET framework_version_label = 'rewritten'
     WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND assessment_framework_id = '0196a001-1111-7111-8111-111111111111';
    RAISE EXCEPTION 'assessment framework meaning was mutable';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.assessment_scale
       SET assessment_framework_id = '0196a001-1111-7111-8111-111111111113'
     WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND assessment_scale_id = '0196a002-1111-7111-8111-111111111111';
    RAISE EXCEPTION 'assessment scale meaning was mutable';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.assessment_scale_value
       SET score_value = 4
     WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND scale_value_id = '0196a003-1111-7111-8111-111111111111';
    RAISE EXCEPTION 'assessment scale value meaning was mutable';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.assessment_dimension
       SET assessment_scale_id = '0196a002-1111-7111-8111-111111111112'
     WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND assessment_dimension_id = '0196a004-1111-7111-8111-111111111111';
    RAISE EXCEPTION 'assessment dimension meaning was mutable';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.assessment_cycle
       SET assessment_framework_id = '0196a001-1111-7111-8111-111111111113'
     WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND assessment_cycle_id = '0196a005-1111-7111-8111-111111111111';
    RAISE EXCEPTION 'assessment cycle meaning was mutable';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.object_assessment
       SET assessor_note = 'rewritten after decision'
     WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND object_assessment_id = '0196a007-1111-7111-8111-111111111114';
    RAISE EXCEPTION 'historical object assessment was mutable';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

UPDATE architecture_core.object_assessment
   SET superseded_at = clock_timestamp()
 WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
   AND object_assessment_id = '0196a007-1111-7111-8111-111111111114';

DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.object_assessment
       SET superseded_at = superseded_at + interval '1 second'
     WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND object_assessment_id = '0196a007-1111-7111-8111-111111111114';
    RAISE EXCEPTION 'assessment supersession timestamp was rewritable';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

SET ROLE ea_runtime;
SET app.tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711';
DO $$
DECLARE
  visible_framework_count integer;
BEGIN
  SELECT count(*)
    INTO visible_framework_count
    FROM architecture_core.assessment_framework;
  IF visible_framework_count <> 2 THEN
    RAISE EXCEPTION 'tenant RLS leaked or hid assessment frameworks: %', visible_framework_count;
  END IF;
END;
$$;
RESET ROLE;
