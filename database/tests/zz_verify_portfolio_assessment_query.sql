\set ON_ERROR_STOP on

-- Buyer acceptance for the purpose-bound portfolio assessment read port.
-- It proves bitemporal cutoffs, truth filtering, tenant binding, and runtime
-- privilege narrowing against the normalized assessment model.

DO $$
BEGIN
  IF to_regprocedure(
      'architecture_core.read_portfolio_assessment_for_tenant(uuid,uuid,timestamptz,timestamptz,text,text)'
     ) IS NULL THEN
    RAISE EXCEPTION 'portfolio assessment query port is missing';
  END IF;
END;
$$;

-- The foundation fixture ends its first authoritative object revision before
-- the assessment cycle begins, while verify_review_integrity.sql deliberately
-- persists proposed revision 2. Add authoritative revision 3 so this read test
-- exercises the object/assessment valid-time intersection without colliding
-- with the cumulative review-integrity fixture.
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

SELECT pg_catalog.set_config(
    'app.portfolio_supersession_cutoff',
    (
      superseded_at - interval '1 microsecond'
    )::text,
    false
)
  FROM architecture_core.object_assessment
 WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
   AND object_assessment_id = '0196a007-1111-7111-8111-111111111114';

-- Reapply the production runtime boundary after the foundation RLS fixture
-- grants broad privileges to ea_runtime for its earlier checks.
\ir ../init/003_grant_runtime_access.sql

SET ROLE ea_runtime;
SET app.tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711';

DO $$
DECLARE
  supersession_cutoff timestamptz;
  historical_count integer;
  current_count integer;
  foreign_count integer;
BEGIN
  supersession_cutoff := pg_catalog.current_setting(
      'app.portfolio_supersession_cutoff'
  )::timestamptz;

  -- The preceding system-cutoff fixture adds another inferred dimension.
  -- Scope this assertion to the review fact under test.
  SELECT count(*)
    INTO historical_count
    FROM architecture_core.read_portfolio_assessment_for_tenant(
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '2026-08-15T00:00:00Z',
        supersession_cutoff,
        'technology_risk',
        'fy2026_q3'
    )
   WHERE truth_status_code = 'authoritative';
  IF historical_count <> 1 THEN
    RAISE EXCEPTION 'historical authoritative assessment was not projected: %', historical_count;
  END IF;

  SELECT count(*)
    INTO current_count
    FROM architecture_core.read_portfolio_assessment_for_tenant(
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '2026-08-15T00:00:00Z',
        supersession_cutoff + interval '1 second',
        'technology_risk',
        'fy2026_q3'
    )
   WHERE truth_status_code = 'inferred'
     AND assessment_dimension_code = 'support_risk';
  IF current_count <> 1 THEN
    RAISE EXCEPTION 'inferred assessment was not preserved as review evidence: %', current_count;
  END IF;

  SELECT count(*)
    INTO foreign_count
    FROM architecture_core.read_portfolio_assessment_for_tenant(
        '0195d145-64e8-7f4f-8a23-a0cc784cb712',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '2026-08-15T00:00:00Z',
        supersession_cutoff,
        'technology_risk',
        'fy2026_q3'
    );
  IF foreign_count <> 0 THEN
    RAISE EXCEPTION 'portfolio assessment query crossed tenant boundary: %', foreign_count;
  END IF;
END;
$$;

DO $$
BEGIN
  IF NOT has_function_privilege(
      current_user,
      'architecture_core.read_portfolio_assessment_for_tenant(uuid,uuid,timestamptz,timestamptz,text,text)',
      'EXECUTE'
  ) THEN
    RAISE EXCEPTION 'runtime role lacks the purpose-bound portfolio read grant';
  END IF;
  IF has_table_privilege(current_user, 'architecture_core.object_assessment', 'SELECT') THEN
    RAISE EXCEPTION 'runtime role has direct object assessment table access';
  END IF;
END;
$$;

RESET ROLE;

-- Keep this acceptance file isolated from later trigger/RLS fixtures. The
-- foundation test intentionally gives ea_runtime broad table authority for
-- those tests; the production boundary itself was asserted above.
GRANT USAGE ON SCHEMA architecture_core TO ea_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA architecture_core TO ea_runtime;
GRANT EXECUTE
    ON ALL FUNCTIONS IN SCHEMA architecture_core TO ea_runtime;
