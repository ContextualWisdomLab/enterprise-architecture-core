BEGIN;

CREATE TABLE architecture_core.data_management_assessment_projection (
    tenant_record_id uuid NOT NULL,
    data_management_assessment_projection_id uuid NOT NULL DEFAULT uuidv7(),
    projection_receipt_id uuid NOT NULL,
    assessment_result_uri text NOT NULL,
    subject_capability_object_id uuid NOT NULL,
    framework_code text NOT NULL,
    framework_version_label text NOT NULL,
    profile_code text NOT NULL,
    knowledge_cutoff_at timestamptz NOT NULL,
    source_recorded_at timestamptz NOT NULL,
    overall_score_basis_points integer NOT NULL,
    readiness_code text NOT NULL,
    truth_status_code text NOT NULL,
    provenance_evidence_uri text NOT NULL,
    provenance_sha256 text NOT NULL,
    provenance_source_locator text,
    supersedes_assessment_result_uri text,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    superseded_at timestamptz,
    CONSTRAINT data_management_assessment_projection_primary_key
        PRIMARY KEY (
            tenant_record_id,
            data_management_assessment_projection_id
        ),
    CONSTRAINT data_management_assessment_projection_tenant_foreign
        FOREIGN KEY (tenant_record_id)
        REFERENCES architecture_core.tenant_record (tenant_record_id),
    CONSTRAINT data_management_assessment_projection_receipt_foreign
        FOREIGN KEY (tenant_record_id, projection_receipt_id)
        REFERENCES architecture_core.projection_receipt
            (tenant_record_id, projection_receipt_id),
    CONSTRAINT data_management_assessment_projection_capability_foreign
        FOREIGN KEY (tenant_record_id, subject_capability_object_id)
        REFERENCES architecture_core.business_capability
            (tenant_record_id, architecture_object_id),
    CONSTRAINT data_management_assessment_projection_uuid_version
        CHECK (
            uuid_extract_version(data_management_assessment_projection_id) = 7
        ),
    CONSTRAINT data_management_assessment_projection_result_uri_format
        CHECK (
            assessment_result_uri ~
            '^urn:cwl:(?=[^:]{2,63}:)[a-z][a-z0-9]+(?:_[a-z0-9]+)*:data_context:data_management_assessment:[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT data_management_assessment_projection_framework_format
        CHECK (
            framework_code ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
            AND length(framework_code) BETWEEN 2 AND 128
        ),
    CONSTRAINT data_management_assessment_projection_version_nonempty
        CHECK (length(btrim(framework_version_label)) BETWEEN 1 AND 64),
    CONSTRAINT data_management_assessment_projection_profile_format
        CHECK (
            profile_code ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
            AND length(profile_code) BETWEEN 2 AND 128
        ),
    CONSTRAINT data_management_assessment_projection_source_time_order
        CHECK (source_recorded_at >= knowledge_cutoff_at),
    CONSTRAINT data_management_assessment_projection_score_bounds
        CHECK (overall_score_basis_points BETWEEN 0 AND 10000),
    CONSTRAINT data_management_assessment_projection_readiness_allowed
        CHECK (readiness_code IN ('evidence_complete', 'evidence_gap')),
    CONSTRAINT data_management_assessment_projection_truth_allowed
        CHECK (
            truth_status_code IN (
                'authoritative',
                'observed',
                'inferred',
                'proposed',
                'superseded',
                'rejected'
            )
        ),
    CONSTRAINT data_management_assessment_projection_evidence_uri_format
        CHECK (
            provenance_evidence_uri ~
            '^urn:cwl:(?=[^:]{2,63}:)[a-z][a-z0-9]+(?:_[a-z0-9]+)*:(?=[^:]{2,63}:)[a-z][a-z0-9]+(?:_[a-z0-9]+)*:(?=[^:]{2,63}:)[a-z][a-z0-9]+(?:_[a-z0-9]+)*:[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT data_management_assessment_projection_digest_format
        CHECK (provenance_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT data_management_assessment_projection_locator_length
        CHECK (
            provenance_source_locator IS NULL
            OR length(provenance_source_locator) BETWEEN 1 AND 2048
        ),
    CONSTRAINT data_management_assessment_projection_supersedes_format
        CHECK (
            supersedes_assessment_result_uri IS NULL
            OR supersedes_assessment_result_uri ~
            '^urn:cwl:(?=[^:]{2,63}:)[a-z][a-z0-9]+(?:_[a-z0-9]+)*:data_context:data_management_assessment:[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT data_management_assessment_projection_system_interval
        CHECK (superseded_at IS NULL OR superseded_at >= recorded_at),
    CONSTRAINT data_management_assessment_projection_identity_unique
        UNIQUE (tenant_record_id, assessment_result_uri),
    CONSTRAINT data_management_assessment_projection_supersedes_unique
        UNIQUE (tenant_record_id, supersedes_assessment_result_uri)
);

CREATE TABLE architecture_core.assessment_missing_evidence_projection (
    tenant_record_id uuid NOT NULL,
    data_management_assessment_projection_id uuid NOT NULL,
    missing_evidence_code text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT assessment_missing_evidence_projection_primary_key
        PRIMARY KEY (
            tenant_record_id,
            data_management_assessment_projection_id,
            missing_evidence_code
        ),
    CONSTRAINT assessment_missing_evidence_projection_assessment_foreign
        FOREIGN KEY (
            tenant_record_id,
            data_management_assessment_projection_id
        ) REFERENCES architecture_core.data_management_assessment_projection (
            tenant_record_id,
            data_management_assessment_projection_id
        ),
    CONSTRAINT assessment_missing_evidence_projection_code_format
        CHECK (
            missing_evidence_code ~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
            AND length(missing_evidence_code) BETWEEN 2 AND 128
        )
);

CREATE TABLE architecture_core.assessment_improvement_plan (
    tenant_record_id uuid NOT NULL,
    assessment_improvement_plan_id uuid NOT NULL DEFAULT uuidv7(),
    data_management_assessment_projection_id uuid NOT NULL,
    missing_evidence_code text NOT NULL,
    decision_request_id uuid NOT NULL,
    target_capability_object_id uuid NOT NULL,
    accountable_organization_object_id uuid NOT NULL,
    remediation_initiative_id uuid NOT NULL,
    initiative_milestone_id uuid NOT NULL,
    funding_reference text,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT assessment_improvement_plan_primary_key
        PRIMARY KEY (tenant_record_id, assessment_improvement_plan_id),
    CONSTRAINT assessment_improvement_plan_gap_foreign
        FOREIGN KEY (
            tenant_record_id,
            data_management_assessment_projection_id,
            missing_evidence_code
        ) REFERENCES architecture_core.assessment_missing_evidence_projection (
            tenant_record_id,
            data_management_assessment_projection_id,
            missing_evidence_code
        ),
    CONSTRAINT assessment_improvement_plan_capability_foreign
        FOREIGN KEY (tenant_record_id, target_capability_object_id)
        REFERENCES architecture_core.business_capability
            (tenant_record_id, architecture_object_id),
    CONSTRAINT assessment_improvement_plan_organization_foreign
        FOREIGN KEY (tenant_record_id, accountable_organization_object_id)
        REFERENCES architecture_core.organization_unit
            (tenant_record_id, architecture_object_id),
    CONSTRAINT assessment_improvement_plan_initiative_foreign
        FOREIGN KEY (tenant_record_id, remediation_initiative_id)
        REFERENCES architecture_core.remediation_initiative
            (tenant_record_id, remediation_initiative_id),
    CONSTRAINT assessment_improvement_plan_milestone_foreign
        FOREIGN KEY (tenant_record_id, initiative_milestone_id)
        REFERENCES architecture_core.initiative_milestone
            (tenant_record_id, initiative_milestone_id),
    CONSTRAINT assessment_improvement_plan_uuid_version
        CHECK (uuid_extract_version(assessment_improvement_plan_id) = 7),
    CONSTRAINT assessment_improvement_plan_decision_uuid_version
        CHECK (uuid_extract_version(decision_request_id) = 7),
    CONSTRAINT assessment_improvement_plan_funding_length
        CHECK (
            funding_reference IS NULL
            OR length(funding_reference) BETWEEN 1 AND 2048
        ),
    CONSTRAINT assessment_improvement_plan_decision_unique
        UNIQUE (tenant_record_id, decision_request_id),
    CONSTRAINT assessment_improvement_plan_gap_unique
        UNIQUE (
            tenant_record_id,
            data_management_assessment_projection_id,
            missing_evidence_code
        )
);

ALTER TABLE architecture_core.data_management_assessment_projection
    ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.data_management_assessment_projection
    FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy
ON architecture_core.data_management_assessment_projection
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.assessment_missing_evidence_projection
    ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.assessment_missing_evidence_projection
    FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy
ON architecture_core.assessment_missing_evidence_projection
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.assessment_improvement_plan
    ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.assessment_improvement_plan
    FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy
ON architecture_core.assessment_improvement_plan
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

CREATE INDEX data_management_assessment_projection_subject_index
    ON architecture_core.data_management_assessment_projection
        (tenant_record_id, subject_capability_object_id, source_recorded_at DESC)
    WHERE superseded_at IS NULL;

CREATE INDEX assessment_improvement_plan_accountability_index
    ON architecture_core.assessment_improvement_plan
        (tenant_record_id, accountable_organization_object_id, recorded_at DESC);

CREATE FUNCTION architecture_core.reject_data_management_projection_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'data-management assessment projection history cannot be hard-deleted';
  END IF;

  IF OLD.superseded_at IS NOT NULL
     AND NEW.superseded_at IS DISTINCT FROM OLD.superseded_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment projection supersession time is immutable once recorded';
  END IF;

  IF NEW.tenant_record_id IS DISTINCT FROM OLD.tenant_record_id
     OR NEW.data_management_assessment_projection_id IS DISTINCT FROM
        OLD.data_management_assessment_projection_id
     OR NEW.projection_receipt_id IS DISTINCT FROM OLD.projection_receipt_id
     OR NEW.assessment_result_uri IS DISTINCT FROM OLD.assessment_result_uri
     OR NEW.subject_capability_object_id IS DISTINCT FROM
        OLD.subject_capability_object_id
     OR NEW.framework_code IS DISTINCT FROM OLD.framework_code
     OR NEW.framework_version_label IS DISTINCT FROM OLD.framework_version_label
     OR NEW.profile_code IS DISTINCT FROM OLD.profile_code
     OR NEW.knowledge_cutoff_at IS DISTINCT FROM OLD.knowledge_cutoff_at
     OR NEW.source_recorded_at IS DISTINCT FROM OLD.source_recorded_at
     OR NEW.overall_score_basis_points IS DISTINCT FROM OLD.overall_score_basis_points
     OR NEW.readiness_code IS DISTINCT FROM OLD.readiness_code
     OR NEW.truth_status_code IS DISTINCT FROM OLD.truth_status_code
     OR NEW.provenance_evidence_uri IS DISTINCT FROM OLD.provenance_evidence_uri
     OR NEW.provenance_sha256 IS DISTINCT FROM OLD.provenance_sha256
     OR NEW.provenance_source_locator IS DISTINCT FROM OLD.provenance_source_locator
     OR NEW.supersedes_assessment_result_uri IS DISTINCT FROM
        OLD.supersedes_assessment_result_uri
     OR NEW.recorded_at IS DISTINCT FROM OLD.recorded_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'data-management assessment projection meaning is immutable';
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER data_management_assessment_projection_guard
BEFORE UPDATE OR DELETE
ON architecture_core.data_management_assessment_projection
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_data_management_projection_mutation();

CREATE FUNCTION architecture_core.reject_assessment_missing_evidence_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION USING
    ERRCODE = '23514',
    MESSAGE = 'projected missing-evidence meaning is immutable';
END;
$$;

CREATE TRIGGER assessment_missing_evidence_projection_update_guard
BEFORE UPDATE ON architecture_core.assessment_missing_evidence_projection
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_assessment_missing_evidence_mutation();

CREATE TRIGGER assessment_missing_evidence_projection_delete_guard
BEFORE DELETE ON architecture_core.assessment_missing_evidence_projection
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_assessment_missing_evidence_mutation();

CREATE FUNCTION architecture_core.reject_assessment_improvement_plan_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION USING
    ERRCODE = '23514',
    MESSAGE = 'assessment improvement-plan evidence is immutable';
END;
$$;

CREATE TRIGGER assessment_improvement_plan_update_guard
BEFORE UPDATE ON architecture_core.assessment_improvement_plan
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_assessment_improvement_plan_mutation();

CREATE TRIGGER assessment_improvement_plan_delete_guard
BEFORE DELETE ON architecture_core.assessment_improvement_plan
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_assessment_improvement_plan_mutation();

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
  active_tenant_id uuid;
  active_tenant_code text;
  subject_capability_id uuid;
  result_identifier uuid;
  receipt_source_code text;
  receipt_status_code text;
  receipt_processed_at timestamptz;
  normalized_missing_codes text[];
  existing_projection_id uuid;
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
  RETURNING data_management_assessment_projection_id
    INTO inserted_projection_id;

  INSERT INTO architecture_core.assessment_missing_evidence_projection (
      tenant_record_id,
      data_management_assessment_projection_id,
      missing_evidence_code
  )
  SELECT active_tenant_id, inserted_projection_id, missing_code
    FROM pg_catalog.unnest(normalized_missing_codes) AS missing_code;

  IF superseded_projection_id IS NOT NULL THEN
    UPDATE architecture_core.data_management_assessment_projection
       SET superseded_at = clock_timestamp()
     WHERE tenant_record_id = active_tenant_id
       AND data_management_assessment_projection_id = superseded_projection_id;
  END IF;

  RETURN QUERY SELECT inserted_projection_id;
END;
$$;

CREATE FUNCTION architecture_core.create_data_management_improvement_plan(
    requested_assessment_projection_id uuid,
    requested_missing_evidence_code text,
    requested_decision_request_id uuid,
    requested_target_capability_object_id uuid,
    requested_accountable_organization_object_id uuid,
    requested_initiative_code text,
    requested_initiative_title text,
    requested_milestone_code text,
    requested_milestone_title text,
    requested_due_at timestamptz,
    requested_funding_reference text
)
RETURNS TABLE (
    assessment_improvement_plan_id uuid,
    remediation_initiative_id uuid,
    initiative_milestone_id uuid,
    outbox_event_id uuid
)
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
  active_tenant_id uuid;
  source_result_uri text;
  source_recorded_at timestamptz;
  source_truth_status_code text;
  source_superseded_at timestamptz;
  source_readiness_code text;
  existing_plan architecture_core.assessment_improvement_plan%ROWTYPE;
  existing_initiative architecture_core.remediation_initiative%ROWTYPE;
  existing_milestone architecture_core.initiative_milestone%ROWTYPE;
  existing_event_id uuid;
  inserted_plan_id uuid;
  inserted_initiative_id uuid;
  inserted_milestone_id uuid;
  inserted_event_id uuid;
BEGIN
  active_tenant_id := architecture_core.current_tenant_id();
  IF active_tenant_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'verified tenant context is required for assessment improvement planning';
  END IF;

  IF requested_assessment_projection_id IS NULL
     OR requested_missing_evidence_code IS NULL
     OR requested_decision_request_id IS NULL
     OR requested_target_capability_object_id IS NULL
     OR requested_accountable_organization_object_id IS NULL
     OR requested_initiative_code IS NULL
     OR requested_initiative_title IS NULL
     OR requested_milestone_code IS NULL
     OR requested_milestone_title IS NULL
     OR requested_due_at IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment improvement planning requires source gap, decision, accountability, initiative, milestone, and due time';
  END IF;

  IF uuid_extract_version(requested_assessment_projection_id) <> 7
     OR uuid_extract_version(requested_decision_request_id) <> 7
     OR uuid_extract_version(requested_target_capability_object_id) <> 7
     OR uuid_extract_version(requested_accountable_organization_object_id) <> 7
     OR requested_missing_evidence_code !~ '^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$'
     OR length(requested_missing_evidence_code) NOT BETWEEN 2 AND 128
     OR requested_initiative_code !~ '^[a-z][a-z0-9]+(?:_[a-z0-9]+)*$'
     OR length(requested_initiative_code) > 128
     OR length(btrim(requested_initiative_title)) NOT BETWEEN 1 AND 512
     OR requested_milestone_code !~ '^[a-z][a-z0-9]+(?:_[a-z0-9]+)*$'
     OR length(requested_milestone_code) > 128
     OR length(btrim(requested_milestone_title)) NOT BETWEEN 1 AND 512
     OR (
        requested_funding_reference IS NOT NULL
        AND length(requested_funding_reference) NOT BETWEEN 1 AND 2048
     ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment improvement decision fields are invalid or exceed bounds';
  END IF;

  SELECT
      projection_record.assessment_result_uri,
      projection_record.source_recorded_at,
      projection_record.truth_status_code,
      projection_record.superseded_at,
      projection_record.readiness_code
    INTO
      source_result_uri,
      source_recorded_at,
      source_truth_status_code,
      source_superseded_at,
      source_readiness_code
    FROM architecture_core.data_management_assessment_projection AS projection_record
    JOIN architecture_core.assessment_missing_evidence_projection AS missing_record
      ON missing_record.tenant_record_id = projection_record.tenant_record_id
     AND missing_record.data_management_assessment_projection_id =
         projection_record.data_management_assessment_projection_id
     AND missing_record.missing_evidence_code = requested_missing_evidence_code
   WHERE projection_record.tenant_record_id = active_tenant_id
     AND projection_record.data_management_assessment_projection_id =
         requested_assessment_projection_id
   FOR UPDATE OF projection_record;

  IF source_result_uri IS NULL
     OR source_readiness_code IS DISTINCT FROM 'evidence_gap'
     OR source_superseded_at IS NOT NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'improvement planning requires an active projected missing-evidence gap';
  END IF;

  IF requested_due_at <= source_recorded_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'improvement milestone must follow the source assessment recording time';
  END IF;

  PERFORM 1
    FROM architecture_core.business_capability AS capability_record
   WHERE capability_record.tenant_record_id = active_tenant_id
     AND capability_record.architecture_object_id =
         requested_target_capability_object_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'target capability is unavailable for the verified tenant';
  END IF;

  PERFORM 1
    FROM architecture_core.organization_unit AS organization_record
   WHERE organization_record.tenant_record_id = active_tenant_id
     AND organization_record.architecture_object_id =
         requested_accountable_organization_object_id;
  IF NOT FOUND THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'accountable organization is unavailable for the verified tenant';
  END IF;

  SELECT plan_record.*
    INTO existing_plan
    FROM architecture_core.assessment_improvement_plan AS plan_record
   WHERE plan_record.tenant_record_id = active_tenant_id
     AND plan_record.decision_request_id = requested_decision_request_id;

  IF existing_plan.assessment_improvement_plan_id IS NOT NULL THEN
    SELECT initiative_record.*
      INTO existing_initiative
      FROM architecture_core.remediation_initiative AS initiative_record
     WHERE initiative_record.tenant_record_id = active_tenant_id
       AND initiative_record.remediation_initiative_id =
           existing_plan.remediation_initiative_id;

    SELECT milestone_record.*
      INTO existing_milestone
      FROM architecture_core.initiative_milestone AS milestone_record
     WHERE milestone_record.tenant_record_id = active_tenant_id
       AND milestone_record.initiative_milestone_id =
           existing_plan.initiative_milestone_id;

    IF existing_plan.data_management_assessment_projection_id IS DISTINCT FROM
           requested_assessment_projection_id
       OR existing_plan.missing_evidence_code IS DISTINCT FROM
           requested_missing_evidence_code
       OR existing_plan.target_capability_object_id IS DISTINCT FROM
           requested_target_capability_object_id
       OR existing_plan.accountable_organization_object_id IS DISTINCT FROM
           requested_accountable_organization_object_id
       OR existing_plan.funding_reference IS DISTINCT FROM requested_funding_reference
       OR existing_initiative.initiative_code IS DISTINCT FROM requested_initiative_code
       OR existing_initiative.initiative_title IS DISTINCT FROM requested_initiative_title
       OR existing_milestone.milestone_code IS DISTINCT FROM requested_milestone_code
       OR existing_milestone.milestone_title IS DISTINCT FROM requested_milestone_title
       OR existing_milestone.target_at IS DISTINCT FROM requested_due_at THEN
      RAISE EXCEPTION USING
        ERRCODE = '23505',
        MESSAGE = 'decision request id already represents different improvement-plan meaning';
    END IF;

    SELECT event_record.outbox_event_id
      INTO existing_event_id
      FROM architecture_core.outbox_event AS event_record
     WHERE event_record.tenant_record_id = active_tenant_id
       AND event_record.decision_request_id = requested_decision_request_id
       AND event_record.event_type_code =
           'org.contextualwisdomlab.ea.data_management.improvement_initiative_created.v1';

    IF existing_event_id IS NULL THEN
      RAISE EXCEPTION USING
        ERRCODE = '23514',
        MESSAGE = 'improvement-plan evidence exists without transactional outbox evidence';
    END IF;

    RETURN QUERY
    SELECT
      existing_plan.assessment_improvement_plan_id,
      existing_plan.remediation_initiative_id,
      existing_plan.initiative_milestone_id,
      existing_event_id;
    RETURN;
  END IF;

  INSERT INTO architecture_core.remediation_initiative (
      tenant_record_id,
      initiative_code,
      initiative_title,
      initiative_description,
      valid_from,
      truth_status_code
  ) VALUES (
      active_tenant_id,
      requested_initiative_code,
      requested_initiative_title,
      'Proposed from projected data-management assessment gap: ' ||
          requested_missing_evidence_code,
      source_recorded_at,
      'proposed'
  )
  RETURNING remediation_initiative_id
    INTO inserted_initiative_id;

  INSERT INTO architecture_core.initiative_milestone (
      tenant_record_id,
      remediation_initiative_id,
      milestone_code,
      milestone_title,
      milestone_description,
      sequence_number,
      target_at,
      valid_from,
      truth_status_code
  ) VALUES (
      active_tenant_id,
      inserted_initiative_id,
      requested_milestone_code,
      requested_milestone_title,
      'Proposed evidence-closure milestone; requires human authorization before execution.',
      1,
      requested_due_at,
      source_recorded_at,
      'proposed'
  )
  RETURNING initiative_milestone_id
    INTO inserted_milestone_id;

  INSERT INTO architecture_core.assessment_improvement_plan (
      tenant_record_id,
      data_management_assessment_projection_id,
      missing_evidence_code,
      decision_request_id,
      target_capability_object_id,
      accountable_organization_object_id,
      remediation_initiative_id,
      initiative_milestone_id,
      funding_reference
  ) VALUES (
      active_tenant_id,
      requested_assessment_projection_id,
      requested_missing_evidence_code,
      requested_decision_request_id,
      requested_target_capability_object_id,
      requested_accountable_organization_object_id,
      inserted_initiative_id,
      inserted_milestone_id,
      requested_funding_reference
  )
  RETURNING assessment_improvement_plan_id
    INTO inserted_plan_id;

  INSERT INTO architecture_core.outbox_event (
      tenant_record_id,
      aggregate_object_id,
      architecture_transformation_id,
      event_type_code,
      event_payload_json,
      event_schema_version,
      decision_request_id
  ) VALUES (
      active_tenant_id,
      requested_target_capability_object_id,
      NULL,
      'org.contextualwisdomlab.ea.data_management.improvement_initiative_created.v1',
      pg_catalog.jsonb_build_object(
          'assessment_result_uri', source_result_uri,
          'missing_evidence_code', requested_missing_evidence_code,
          'target_capability_object_id', requested_target_capability_object_id,
          'accountable_organization_object_id',
          requested_accountable_organization_object_id,
          'remediation_initiative_id', inserted_initiative_id,
          'initiative_milestone_id', inserted_milestone_id,
          'decision_request_id', requested_decision_request_id,
          'due_at', requested_due_at,
          'source_truth_status_code', source_truth_status_code,
          'initiative_truth_status_code', 'proposed',
          'next_action', 'review_and_authorize_improvement_initiative'
      ),
      '1.0.0',
      requested_decision_request_id
  )
  RETURNING outbox_event.outbox_event_id
    INTO inserted_event_id;

  RETURN QUERY
  SELECT
    inserted_plan_id,
    inserted_initiative_id,
    inserted_milestone_id,
    inserted_event_id;
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

REVOKE ALL
ON FUNCTION architecture_core.create_data_management_improvement_plan(
    uuid,
    text,
    uuid,
    uuid,
    uuid,
    text,
    text,
    text,
    text,
    timestamptz,
    text
)
FROM PUBLIC;

COMMENT ON TABLE architecture_core.data_management_assessment_projection IS
'Immutable tenant-scoped projection of a semantic-data-portal-owned data-management assessment result. It preserves source truth, provenance, knowledge cutoff, source recording time, and supersession without claiming assessment authority in EA Core.';

COMMENT ON TABLE architecture_core.assessment_missing_evidence_projection IS
'Normalized immutable missing-evidence codes from one projected data-management assessment result; publisher-owned diagnostic prose and scoring rules are never copied here.';

COMMENT ON TABLE architecture_core.assessment_improvement_plan IS
'Immutable EA decision evidence linking one projected assessment gap to a proposed remediation initiative, target capability, accountable organization, milestone, and idempotent decision request. Projection truth never silently becomes authoritative EA truth.';

COMMIT;
