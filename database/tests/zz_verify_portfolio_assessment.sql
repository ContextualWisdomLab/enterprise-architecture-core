\set ON_ERROR_STOP on

-- Buyer acceptance for versioned portfolio assessment. This file is intentionally
-- added before migration 0010 so the first branch commit is RED: the required
-- normalized assessment relations do not yet exist.

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
    assessment_framework_id,
    assessment_scale_id,
    dimension_code,
    dimension_title
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196a004-1111-7111-8111-111111111111',
    '0196a001-1111-7111-8111-111111111111',
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
