BEGIN;

ALTER FUNCTION architecture_core.record_data_management_assessment_result(
    uuid,
    text,
    text,
    text,
    text,
    text,
    timestamptz,
    timestamptz,
    integer,
    text,
    text,
    text,
    text,
    text,
    text,
    text[]
)
RENAME TO record_data_management_assessment_result_internal;

REVOKE ALL
ON FUNCTION architecture_core.record_data_management_assessment_result_internal(
    uuid,
    text,
    text,
    text,
    text,
    text,
    timestamptz,
    timestamptz,
    integer,
    text,
    text,
    text,
    text,
    text,
    text,
    text[]
)
FROM PUBLIC;

CREATE FUNCTION architecture_core.record_data_management_assessment_result(
    requested_projection_receipt_id uuid,
    requested_assessment_result_uri text,
    requested_subject_ref text,
    requested_framework_code text,
    requested_framework_version text,
    requested_profile_code text,
    requested_knowledge_cutoff_at timestamptz,
    requested_source_recorded_at timestamptz,
    requested_overall_score_basis_points integer,
    requested_readiness_code text,
    requested_truth_status_code text,
    requested_provenance_evidence_uri text,
    requested_provenance_sha256 text,
    requested_provenance_source_locator text,
    requested_supersedes_result_ref text,
    requested_missing_evidence_codes text[]
)
RETURNS TABLE (
    data_management_assessment_projection_id uuid
)
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
  requested_code_count integer;
  distinct_code_count integer;
BEGIN
  IF requested_missing_evidence_codes IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'missing_evidence_codes is required by the data-management assessment contract';
  END IF;

  requested_code_count := pg_catalog.cardinality(requested_missing_evidence_codes);
  IF requested_code_count > 256 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'missing_evidence_codes exceeds the contract maximum of 256 items';
  END IF;

  IF EXISTS (
      SELECT 1
        FROM pg_catalog.unnest(requested_missing_evidence_codes) AS missing_code
       WHERE missing_code IS NULL
          OR missing_code !~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
          OR pg_catalog.length(missing_code) NOT BETWEEN 2 AND 128
  ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'missing_evidence_codes must contain canonical code strings without normalization';
  END IF;

  SELECT count(DISTINCT missing_code)
    INTO distinct_code_count
    FROM pg_catalog.unnest(requested_missing_evidence_codes) AS missing_code;

  IF distinct_code_count <> requested_code_count THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'missing_evidence_codes must be unique; duplicate source values are not normalized';
  END IF;

  RETURN QUERY
  SELECT result.data_management_assessment_projection_id
    FROM architecture_core.record_data_management_assessment_result_internal(
      requested_projection_receipt_id,
      requested_assessment_result_uri,
      requested_subject_ref,
      requested_framework_code,
      requested_framework_version,
      requested_profile_code,
      requested_knowledge_cutoff_at,
      requested_source_recorded_at,
      requested_overall_score_basis_points,
      requested_readiness_code,
      requested_truth_status_code,
      requested_provenance_evidence_uri,
      requested_provenance_sha256,
      requested_provenance_source_locator,
      requested_supersedes_result_ref,
      requested_missing_evidence_codes
    ) AS result;
END;
$$;

REVOKE ALL
ON FUNCTION architecture_core.record_data_management_assessment_result(
    uuid,
    text,
    text,
    text,
    text,
    text,
    timestamptz,
    timestamptz,
    integer,
    text,
    text,
    text,
    text,
    text,
    text,
    text[]
)
FROM PUBLIC;

COMMENT ON FUNCTION architecture_core.record_data_management_assessment_result(
    uuid,
    text,
    text,
    text,
    text,
    text,
    timestamptz,
    timestamptz,
    integer,
    text,
    text,
    text,
    text,
    text,
    text,
    text[]
) IS
'Validates the Context Graph data-management assessment missing-evidence array exactly before projection. Required, bounded, unique canonical source codes fail closed rather than being trimmed, deduplicated, or synthesized.';

COMMENT ON FUNCTION architecture_core.record_data_management_assessment_result_internal(
    uuid,
    text,
    text,
    text,
    text,
    text,
    timestamptz,
    timestamptz,
    integer,
    text,
    text,
    text,
    text,
    text,
    text,
    text[]
) IS
'Internal projection implementation behind the contract-shape guard. It is not an integration port and remains non-executable by PUBLIC.';

COMMIT;