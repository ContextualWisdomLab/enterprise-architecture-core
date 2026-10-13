BEGIN;

CREATE OR REPLACE FUNCTION architecture_core.record_data_management_assessment_result_internal(
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
  active_tenant_id uuid;
  active_tenant_code text;
  subject_capability_id uuid;
  result_identifier uuid;
  receipt_source_code text;
  receipt_status_code text;
  receipt_processed_at timestamptz;
  normalized_missing_codes text[];
  existing_missing_codes text[];
  existing_projection architecture_core.data_management_assessment_projection%ROWTYPE;
  superseded_projection_id uuid;
  inserted_projection_id uuid;
BEGIN
  active_tenant_id := architecture_core.current_tenant_id();
  IF active_tenant_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'verified tenant context is required for assessment projection';
  END IF;

  SELECT tenant_record.tenant_code
    INTO active_tenant_code
    FROM architecture_core.tenant_record AS tenant_record
   WHERE tenant_record.tenant_record_id = active_tenant_id;

  IF active_tenant_code IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment projection tenant is unavailable';
  END IF;

  IF requested_projection_receipt_id IS NULL
     OR requested_assessment_result_uri IS NULL
     OR requested_subject_ref IS NULL
     OR requested_framework_code IS NULL
     OR requested_framework_version IS NULL
     OR requested_profile_code IS NULL
     OR requested_knowledge_cutoff_at IS NULL
     OR requested_source_recorded_at IS NULL
     OR requested_overall_score_basis_points IS NULL
     OR requested_readiness_code IS NULL
     OR requested_truth_status_code IS NULL
     OR requested_provenance_evidence_uri IS NULL
     OR requested_provenance_sha256 IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment projection requires receipt, identity, profile, time, score, truth, and provenance';
  END IF;

  IF requested_framework_code !~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
     OR length(requested_framework_code) NOT BETWEEN 2 AND 128
     OR length(btrim(requested_framework_version)) NOT BETWEEN 1 AND 64
     OR requested_profile_code !~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
     OR length(requested_profile_code) NOT BETWEEN 2 AND 128
     OR requested_overall_score_basis_points NOT BETWEEN 0 AND 10000
     OR requested_readiness_code NOT IN ('evidence_complete', 'evidence_gap')
     OR requested_truth_status_code NOT IN (
        'authoritative', 'observed', 'inferred', 'proposed', 'superseded', 'rejected'
     )
     OR requested_source_recorded_at < requested_knowledge_cutoff_at
     OR requested_provenance_sha256 !~ '^[0-9a-f]{64}$'
     OR (
        requested_provenance_source_locator IS NOT NULL
        AND length(requested_provenance_source_locator) NOT BETWEEN 1 AND 2048
     ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment result violates the provider-neutral data-management contract';
  END IF;

  BEGIN
    result_identifier := split_part(requested_assessment_result_uri, ':', 6)::uuid;
    subject_capability_id := split_part(requested_subject_ref, ':', 6)::uuid;
  EXCEPTION WHEN invalid_text_representation THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment result and subject references require canonical UUIDv7 identities';
  END;

  IF requested_assessment_result_uri IS DISTINCT FROM
       'urn:cwl:' || active_tenant_code || ':data_context:data_management_assessment:' ||
       result_identifier::text
     OR requested_subject_ref IS DISTINCT FROM
       'urn:cwl:' || active_tenant_code || ':ea_core:business_capability:' ||
       subject_capability_id::text
     OR uuid_extract_version(result_identifier) <> 7
     OR uuid_extract_version(subject_capability_id) <> 7 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment result or subject reference crosses the canonical tenant/authority boundary';
  END IF;

  IF requested_provenance_evidence_uri !~
       '^urn:cwl:(?=[^:]{2,63}:)[a-z][a-z0-9]+(?:_[a-z0-9]+)*:(?=[^:]{2,63}:)[a-z][a-z0-9]+(?:_[a-z0-9]+)*:(?=[^:]{2,63}:)[a-z][a-z0-9]+(?:_[a-z0-9]+)*:[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$' THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment provenance evidence requires a canonical CWL object reference';
  END IF;

  SELECT
      split_part(receipt_record.event_source_uri, ':', 4),
      receipt_record.processing_status_code,
      receipt_record.processed_at
    INTO receipt_source_code, receipt_status_code, receipt_processed_at
    FROM architecture_core.projection_receipt AS receipt_record
   WHERE receipt_record.tenant_record_id = active_tenant_id
     AND receipt_record.projection_receipt_id = requested_projection_receipt_id;

  IF receipt_source_code IS DISTINCT FROM 'semantic_data_portal'
     OR receipt_status_code IS DISTINCT FROM 'processed'
     OR receipt_processed_at IS NULL
     OR receipt_processed_at < requested_source_recorded_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment projection requires processed semantic-data-portal receipt evidence';
  END IF;

  PERFORM 1
    FROM architecture_core.business_capability AS capability_record
   WHERE capability_record.tenant_record_id = active_tenant_id
     AND capability_record.architecture_object_id = subject_capability_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment subject capability is unavailable for the verified tenant';
  END IF;

  SELECT COALESCE(
      pg_catalog.array_agg(normalized_code ORDER BY normalized_code),
      ARRAY[]::text[]
  )
    INTO normalized_missing_codes
    FROM (
      SELECT DISTINCT btrim(code_value) AS normalized_code
        FROM pg_catalog.unnest(
          COALESCE(requested_missing_evidence_codes, ARRAY[]::text[])
        ) AS code_value
    ) AS normalized
   WHERE normalized_code <> '';

  IF EXISTS (
      SELECT 1
        FROM pg_catalog.unnest(normalized_missing_codes) AS missing_code
       WHERE missing_code !~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
          OR length(missing_code) NOT BETWEEN 2 AND 128
  )
     OR (
        requested_readiness_code = 'evidence_complete'
        AND pg_catalog.cardinality(normalized_missing_codes) <> 0
     )
     OR (
        requested_readiness_code = 'evidence_gap'
        AND pg_catalog.cardinality(normalized_missing_codes) = 0
     ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment readiness and normalized missing-evidence codes disagree';
  END IF;

  SELECT projection_record.*
    INTO existing_projection
    FROM architecture_core.data_management_assessment_projection AS projection_record
   WHERE projection_record.tenant_record_id = active_tenant_id
     AND projection_record.assessment_result_uri = requested_assessment_result_uri;

  IF existing_projection.data_management_assessment_projection_id IS NOT NULL THEN
    SELECT COALESCE(
        pg_catalog.array_agg(
          missing_record.missing_evidence_code
          ORDER BY missing_record.missing_evidence_code
        ),
        ARRAY[]::text[]
    )
      INTO existing_missing_codes
      FROM architecture_core.assessment_missing_evidence_projection AS missing_record
     WHERE missing_record.tenant_record_id = active_tenant_id
       AND missing_record.data_management_assessment_projection_id =
           existing_projection.data_management_assessment_projection_id;

    IF existing_projection.projection_receipt_id IS DISTINCT FROM
           requested_projection_receipt_id
       OR existing_projection.subject_capability_object_id IS DISTINCT FROM
           subject_capability_id
       OR existing_projection.framework_code IS DISTINCT FROM requested_framework_code
       OR existing_projection.framework_version_label IS DISTINCT FROM
           requested_framework_version
       OR existing_projection.profile_code IS DISTINCT FROM requested_profile_code
       OR existing_projection.knowledge_cutoff_at IS DISTINCT FROM
           requested_knowledge_cutoff_at
       OR existing_projection.source_recorded_at IS DISTINCT FROM
           requested_source_recorded_at
       OR existing_projection.overall_score_basis_points IS DISTINCT FROM
           requested_overall_score_basis_points
       OR existing_projection.readiness_code IS DISTINCT FROM requested_readiness_code
       OR existing_projection.truth_status_code IS DISTINCT FROM
           requested_truth_status_code
       OR existing_projection.provenance_evidence_uri IS DISTINCT FROM
           requested_provenance_evidence_uri
       OR existing_projection.provenance_sha256 IS DISTINCT FROM
           requested_provenance_sha256
       OR existing_projection.provenance_source_locator IS DISTINCT FROM
           requested_provenance_source_locator
       OR existing_projection.supersedes_assessment_result_uri IS DISTINCT FROM
           requested_supersedes_result_ref
       OR existing_missing_codes IS DISTINCT FROM normalized_missing_codes THEN
      RAISE EXCEPTION USING
        ERRCODE = '23505',
        MESSAGE = 'assessment result identity already represents different projected meaning';
    END IF;

    RETURN QUERY
    SELECT existing_projection.data_management_assessment_projection_id;
    RETURN;
  END IF;

  IF requested_supersedes_result_ref IS NOT NULL THEN
    SELECT projection_record.data_management_assessment_projection_id
      INTO superseded_projection_id
      FROM architecture_core.data_management_assessment_projection AS projection_record
     WHERE projection_record.tenant_record_id = active_tenant_id
       AND projection_record.assessment_result_uri = requested_supersedes_result_ref
       AND projection_record.subject_capability_object_id = subject_capability_id
       AND projection_record.framework_code = requested_framework_code
       AND projection_record.framework_version_label = requested_framework_version
       AND projection_record.profile_code = requested_profile_code
       AND projection_record.superseded_at IS NULL
     FOR UPDATE;

    IF superseded_projection_id IS NULL THEN
      RAISE EXCEPTION USING
        ERRCODE = '23514',
        MESSAGE = 'superseded assessment result is unavailable or incompatible';
    END IF;
  END IF;

  INSERT INTO architecture_core.data_management_assessment_projection (
      tenant_record_id,
      projection_receipt_id,
      assessment_result_uri,
      subject_capability_object_id,
      framework_code,
      framework_version_label,
      profile_code,
      knowledge_cutoff_at,
      source_recorded_at,
      overall_score_basis_points,
      readiness_code,
      truth_status_code,
      provenance_evidence_uri,
      provenance_sha256,
      provenance_source_locator,
      supersedes_assessment_result_uri
  ) VALUES (
      active_tenant_id,
      requested_projection_receipt_id,
      requested_assessment_result_uri,
      subject_capability_id,
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
      requested_supersedes_result_ref
  )
  RETURNING
      data_management_assessment_projection.data_management_assessment_projection_id
    INTO inserted_projection_id;

  INSERT INTO architecture_core.assessment_missing_evidence_projection (
      tenant_record_id,
      data_management_assessment_projection_id,
      missing_evidence_code
  )
  SELECT active_tenant_id, inserted_projection_id, missing_code
    FROM pg_catalog.unnest(normalized_missing_codes) AS missing_code;

  IF superseded_projection_id IS NOT NULL THEN
    UPDATE architecture_core.data_management_assessment_projection AS projection_record
       SET superseded_at = clock_timestamp()
     WHERE projection_record.tenant_record_id = active_tenant_id
       AND projection_record.data_management_assessment_projection_id =
           superseded_projection_id;
  END IF;

  RETURN QUERY SELECT inserted_projection_id;
END;
$$;

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
'Preserves the contract-validated data-management assessment result and supersession history. Supersession updates explicitly qualify projection columns so PL/pgSQL output variables cannot shadow persisted identity fields.';

ALTER TABLE architecture_core.data_management_assessment_projection
    ADD COLUMN profile_version text;

DO $$
BEGIN
  IF EXISTS (
      SELECT 1
        FROM architecture_core.data_management_assessment_projection
  ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'profile_version migration cannot infer meaning for pre-existing unreleased assessment projections';
  END IF;
END;
$$;

ALTER TABLE architecture_core.data_management_assessment_projection
    ADD CONSTRAINT data_management_assessment_profile_version_format
    CHECK (
        profile_version ~ '^[0-9]+\.[0-9]+\.[0-9]+$'
        AND length(profile_version) <= 64
    );
ALTER TABLE architecture_core.data_management_assessment_projection
    ALTER COLUMN profile_version SET NOT NULL;

CREATE FUNCTION architecture_core.assign_data_management_profile_version()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
DECLARE
  requested_profile_version text;
BEGIN
  requested_profile_version := current_setting(
      'app.data_management_profile_version',
      true
  );
  IF requested_profile_version IS NULL
     OR requested_profile_version !~ '^[0-9]+\.[0-9]+\.[0-9]+$'
     OR length(requested_profile_version) > 64 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment profile_version requires an exact semantic version';
  END IF;
  NEW.profile_version := requested_profile_version;
  RETURN NEW;
END;
$$;

CREATE TRIGGER data_management_profile_version_insert_guard
BEFORE INSERT ON architecture_core.data_management_assessment_projection
FOR EACH ROW
EXECUTE FUNCTION architecture_core.assign_data_management_profile_version();

CREATE FUNCTION architecture_core.reject_data_management_profile_version_mutation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
  RAISE EXCEPTION USING
    ERRCODE = '23514',
    MESSAGE = 'assessment profile_version is immutable after projection';
END;
$$;

CREATE TRIGGER data_management_profile_version_update_guard
BEFORE UPDATE OF profile_version
ON architecture_core.data_management_assessment_projection
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_data_management_profile_version_mutation();

CREATE OR REPLACE FUNCTION architecture_core.record_data_management_assessment_result(
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
BEGIN
  RAISE EXCEPTION USING
    ERRCODE = '23514',
    MESSAGE = 'assessment profile_version is required by the versioned contract';
END;
$$;

CREATE FUNCTION architecture_core.record_data_management_assessment_result(
    requested_projection_receipt_id uuid,
    requested_assessment_result_uri text,
    requested_subject_ref text,
    requested_framework_code text,
    requested_framework_version text,
    requested_profile_code text,
    requested_profile_version text,
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
  inserted_projection_id uuid;
  stored_profile_version text;
BEGIN
  IF requested_profile_version IS NULL
     OR requested_profile_version !~ '^[0-9]+\.[0-9]+\.[0-9]+$'
     OR length(requested_profile_version) > 64 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'profile_version must be an exact semantic version';
  END IF;

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

  PERFORM pg_catalog.set_config(
      'app.data_management_profile_version',
      requested_profile_version,
      true
  );

  SELECT result.data_management_assessment_projection_id
    INTO inserted_projection_id
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

  SELECT projection.profile_version
    INTO stored_profile_version
    FROM architecture_core.data_management_assessment_projection AS projection
   WHERE projection.tenant_record_id = architecture_core.current_tenant_id()
     AND projection.data_management_assessment_projection_id = inserted_projection_id;

  IF stored_profile_version IS DISTINCT FROM requested_profile_version THEN
    RAISE EXCEPTION USING
      ERRCODE = '23505',
      MESSAGE = 'assessment result identity already represents a different profile_version';
  END IF;

  RETURN QUERY SELECT inserted_projection_id;
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
'Projects a versioned Data/AI Context assessment only when profile_code and exact profile_version are both supplied. Exact result replay must retain the same profile version; omission and semantic-version drift fail closed.';

COMMIT;