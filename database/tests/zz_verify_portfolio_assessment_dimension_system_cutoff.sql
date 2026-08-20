\set ON_ERROR_STOP on

-- A portfolio read at a historical system-time cutoff must not expose
-- assessment definition metadata that was recorded after that cutoff. The
-- normalized dimension is immutable, but its recorded_at still defines when
-- the system first knew that meaning.
INSERT INTO architecture_core.object_revision (
    tenant_record_id,
    object_revision_id,
    architecture_object_id,
    revision_number,
    object_title,
    valid_from,
    truth_status_code,
    evidence_record_id,
    recorded_at
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196a009-1111-7111-8111-111111111111',
    '0195d145-64e8-7f4f-8a23-a0cc784cb902',
    3,
    'Legacy Order Platform',
    '2026-07-01T00:00:00Z',
    'authoritative',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf10',
    '2026-08-20T00:00:00Z'
) ON CONFLICT (tenant_record_id, object_revision_id) DO NOTHING;

INSERT INTO architecture_core.assessment_dimension (
    tenant_record_id,
    assessment_dimension_id,
    assessment_scale_id,
    dimension_code,
    dimension_title,
    recorded_at
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196a004-2222-7222-8222-222222222222',
    '0196a002-1111-7111-8111-111111111111',
    'future_support_risk',
    'Future-recorded vendor support risk',
    '2026-08-21T00:00:00Z'
);

INSERT INTO architecture_core.object_assessment (
    tenant_record_id,
    object_assessment_id,
    architecture_object_id,
    assessment_dimension_id,
    assessment_cycle_id,
    scale_value_id,
    valid_from,
    valid_to,
    recorded_at,
    truth_status_code
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196a007-2222-7222-8222-222222222222',
    '0195d145-64e8-7f4f-8a23-a0cc784cb902',
    '0196a004-2222-7222-8222-222222222222',
    '0196a005-1111-7111-8111-111111111111',
    '0196a003-1111-7111-8111-111111111111',
    '2026-07-01T00:00:00Z',
    '2026-10-01T00:00:00Z',
    '2026-08-20T00:00:00Z',
    'inferred'
);

DO $$
DECLARE
  leaked_future_dimension_count integer;
BEGIN
  SELECT count(*)
    INTO leaked_future_dimension_count
    FROM architecture_core.read_portfolio_assessment_for_tenant(
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '2026-08-15T00:00:00Z',
        '2026-08-20T20:30:00Z',
        'technology_risk',
        'fy2026_q3'
    )
   WHERE assessment_dimension_code = 'future_support_risk';

  IF leaked_future_dimension_count <> 0 THEN
    RAISE EXCEPTION
      'portfolio read leaked % future-recorded dimension definition(s)',
      leaked_future_dimension_count;
  END IF;
END;
$$;
