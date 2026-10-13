BEGIN;

CREATE TABLE architecture_core.external_context_reference (
    tenant_record_id uuid NOT NULL,
    external_context_reference_id uuid NOT NULL DEFAULT uuidv7(),
    reference_authority_code text NOT NULL,
    canonical_object_uri text NOT NULL,
    external_object_kind_code text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT external_context_reference_primary_key
        PRIMARY KEY (tenant_record_id, external_context_reference_id),
    CONSTRAINT external_context_reference_tenant_foreign
        FOREIGN KEY (tenant_record_id)
        REFERENCES architecture_core.tenant_record (tenant_record_id),
    CONSTRAINT external_context_reference_uuid_version
        CHECK (uuid_extract_version(external_context_reference_id) = 7),
    CONSTRAINT external_context_reference_authority_allowed
        CHECK (
            reference_authority_code IN (
                'semantic_data_portal',
                'pg_erd_cloud'
            )
        ),
    CONSTRAINT external_context_reference_kind_allowed
        CHECK (
            external_object_kind_code IN (
                'database_schema',
                'data_product',
                'dashboard',
                'model',
                'ai_agent'
            )
        ),
    CONSTRAINT external_context_reference_owner_boundary
        CHECK (
            (
                reference_authority_code = 'pg_erd_cloud'
                AND external_object_kind_code = 'database_schema'
            )
            OR (
                reference_authority_code = 'semantic_data_portal'
                AND external_object_kind_code IN (
                    'data_product',
                    'dashboard',
                    'model',
                    'ai_agent'
                )
            )
        ),
    CONSTRAINT external_context_reference_uri_format
        CHECK (
            length(canonical_object_uri) BETWEEN 1 AND 2048
            AND canonical_object_uri ~
            '^urn:cwl:(?=[^:]{2,63}:)[a-z][a-z0-9]+(?:_[a-z0-9]+)*:(?=[^:]{2,63}:)[a-z][a-z0-9]+(?:_[a-z0-9]+)*:(?=[^:]{2,63}:)[a-z][a-z0-9]+(?:_[a-z0-9]+)*:[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT external_context_reference_identity_unique
        UNIQUE (tenant_record_id, canonical_object_uri)
);

CREATE TABLE architecture_core.application_context_projection (
    tenant_record_id uuid NOT NULL,
    application_context_projection_id uuid NOT NULL DEFAULT uuidv7(),
    application_object_id uuid NOT NULL,
    external_context_reference_id uuid NOT NULL,
    projection_receipt_id uuid NOT NULL,
    projection_relation_code text NOT NULL,
    truth_status_code text NOT NULL,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    superseded_at timestamptz,
    CONSTRAINT application_context_projection_primary_key
        PRIMARY KEY (tenant_record_id, application_context_projection_id),
    CONSTRAINT application_context_projection_tenant_foreign
        FOREIGN KEY (tenant_record_id)
        REFERENCES architecture_core.tenant_record (tenant_record_id),
    CONSTRAINT application_context_projection_application_foreign
        FOREIGN KEY (tenant_record_id, application_object_id)
        REFERENCES architecture_core.architecture_object
            (tenant_record_id, architecture_object_id),
    CONSTRAINT application_context_projection_reference_foreign
        FOREIGN KEY (tenant_record_id, external_context_reference_id)
        REFERENCES architecture_core.external_context_reference
            (tenant_record_id, external_context_reference_id),
    CONSTRAINT application_context_projection_receipt_foreign
        FOREIGN KEY (tenant_record_id, projection_receipt_id)
        REFERENCES architecture_core.projection_receipt
            (tenant_record_id, projection_receipt_id),
    CONSTRAINT application_context_projection_uuid_version
        CHECK (uuid_extract_version(application_context_projection_id) = 7),
    CONSTRAINT application_context_projection_relation_allowed
        CHECK (
            projection_relation_code IN (
                'depends_on',
                'produces',
                'consumes',
                'impacts'
            )
        ),
    CONSTRAINT application_context_projection_truth_allowed
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
    CONSTRAINT application_context_projection_valid_interval
        CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT application_context_projection_system_interval
        CHECK (superseded_at IS NULL OR superseded_at >= recorded_at)
);

ALTER TABLE architecture_core.application_context_projection
    ADD CONSTRAINT application_context_projection_active_interval_exclusion
    EXCLUDE USING gist (
        tenant_record_id WITH =,
        application_object_id WITH =,
        external_context_reference_id WITH =,
        projection_relation_code WITH =,
        tstzrange(valid_from, valid_to, '[)') WITH &&
    ) WHERE (
        superseded_at IS NULL
        AND truth_status_code IN ('authoritative', 'observed')
    );

CREATE FUNCTION architecture_core.validate_external_context_reference()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  expected_tenant_code text;
  uri_tenant_code text;
  uri_authority_code text;
  uri_object_kind_code text;
BEGIN
  SELECT tenant_code
    INTO expected_tenant_code
    FROM architecture_core.tenant_record
   WHERE tenant_record_id = NEW.tenant_record_id;

  uri_tenant_code := split_part(NEW.canonical_object_uri, ':', 3);
  uri_authority_code := split_part(NEW.canonical_object_uri, ':', 4);
  uri_object_kind_code := split_part(NEW.canonical_object_uri, ':', 5);

  IF expected_tenant_code IS NULL
     OR uri_tenant_code IS DISTINCT FROM expected_tenant_code THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'external context reference tenant does not match row tenant';
  END IF;

  IF uri_authority_code IS DISTINCT FROM NEW.reference_authority_code
     OR uri_object_kind_code IS DISTINCT FROM NEW.external_object_kind_code THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'external context reference authority or kind does not match URI';
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER external_context_reference_guard
BEFORE INSERT
ON architecture_core.external_context_reference
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_external_context_reference();

CREATE FUNCTION architecture_core.reject_external_context_reference_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION USING
    ERRCODE = '23514',
    MESSAGE = 'external context reference identity is immutable';
END;
$$;

CREATE TRIGGER external_context_reference_immutable_guard
BEFORE UPDATE OR DELETE
ON architecture_core.external_context_reference
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_external_context_reference_mutation();

CREATE FUNCTION architecture_core.validate_application_context_projection()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  application_type_code text;
  reference_authority text;
  reference_kind text;
  receipt_source_code text;
  receipt_status_code text;
  receipt_processed_at timestamptz;
BEGIN
  SELECT object_type.object_type_code
    INTO application_type_code
    FROM architecture_core.architecture_object AS architecture_object
    JOIN architecture_core.object_type AS object_type
      ON object_type.object_type_id = architecture_object.object_type_id
   WHERE architecture_object.tenant_record_id = NEW.tenant_record_id
     AND architecture_object.architecture_object_id =
         NEW.application_object_id;

  IF application_type_code IS DISTINCT FROM 'application_record' THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'application context projection requires an application object';
  END IF;

  SELECT
      external_context_reference.reference_authority_code,
      external_context_reference.external_object_kind_code
    INTO reference_authority, reference_kind
    FROM architecture_core.external_context_reference
   WHERE external_context_reference.tenant_record_id = NEW.tenant_record_id
     AND external_context_reference.external_context_reference_id =
         NEW.external_context_reference_id;

  IF reference_authority IS NULL OR reference_kind IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'external context reference is unavailable';
  END IF;

  SELECT
      split_part(projection_receipt.event_source_uri, ':', 4),
      projection_receipt.processing_status_code,
      projection_receipt.processed_at
    INTO receipt_source_code, receipt_status_code, receipt_processed_at
    FROM architecture_core.projection_receipt
   WHERE projection_receipt.tenant_record_id = NEW.tenant_record_id
     AND projection_receipt.projection_receipt_id = NEW.projection_receipt_id;

  IF receipt_source_code IS NULL
     OR receipt_source_code NOT IN (
        'semantic_data_portal',
        'pg_erd_cloud',
        'lineage_weave'
     ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'projection receipt source is not an accepted Context Fabric owner';
  END IF;

  IF receipt_status_code IS DISTINCT FROM 'processed'
     OR receipt_processed_at IS NULL
     OR receipt_processed_at > NEW.recorded_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'projection requires a processed receipt recorded before the fact';
  END IF;

  IF receipt_source_code = 'pg_erd_cloud'
     AND (
        reference_authority <> 'pg_erd_cloud'
        OR reference_kind <> 'database_schema'
        OR NEW.truth_status_code <> 'observed'
     ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'pg-erd-cloud projections are observed physical-schema evidence only';
  END IF;

  IF receipt_source_code = 'semantic_data_portal'
     AND reference_authority <> 'semantic_data_portal' THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'semantic-data-portal may project only its canonical object references';
  END IF;

  IF receipt_source_code = 'lineage_weave'
     AND NEW.truth_status_code NOT IN ('inferred', 'proposed') THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'LineageWeave projections must remain inferred or proposed';
  END IF;

  IF TG_OP = 'UPDATE' THEN
    IF OLD.superseded_at IS NOT NULL
       AND NEW.superseded_at IS DISTINCT FROM OLD.superseded_at THEN
      RAISE EXCEPTION USING
        ERRCODE = '23514',
        MESSAGE = 'application context projection can be superseded only once';
    END IF;

    IF NEW.tenant_record_id IS DISTINCT FROM OLD.tenant_record_id
       OR NEW.application_context_projection_id IS DISTINCT FROM
          OLD.application_context_projection_id
       OR NEW.application_object_id IS DISTINCT FROM OLD.application_object_id
       OR NEW.external_context_reference_id IS DISTINCT FROM
          OLD.external_context_reference_id
       OR NEW.projection_receipt_id IS DISTINCT FROM OLD.projection_receipt_id
       OR NEW.projection_relation_code IS DISTINCT FROM
          OLD.projection_relation_code
       OR NEW.truth_status_code IS DISTINCT FROM OLD.truth_status_code
       OR NEW.valid_from IS DISTINCT FROM OLD.valid_from
       OR NEW.valid_to IS DISTINCT FROM OLD.valid_to
       OR NEW.recorded_at IS DISTINCT FROM OLD.recorded_at THEN
      RAISE EXCEPTION USING
        ERRCODE = '23514',
        MESSAGE = 'application context projection meaning is immutable';
    END IF;
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER application_context_projection_guard
BEFORE INSERT OR UPDATE
ON architecture_core.application_context_projection
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_application_context_projection();

CREATE FUNCTION architecture_core.reject_application_context_projection_delete()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION USING
    ERRCODE = '23514',
    MESSAGE = 'application context projection history cannot be hard-deleted';
END;
$$;

CREATE TRIGGER application_context_projection_delete_guard
BEFORE DELETE
ON architecture_core.application_context_projection
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_application_context_projection_delete();

ALTER TABLE architecture_core.external_context_reference
    ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.external_context_reference
    FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy
ON architecture_core.external_context_reference
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.application_context_projection
    ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.application_context_projection
    FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy
ON architecture_core.application_context_projection
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

CREATE INDEX external_context_reference_authority_index
    ON architecture_core.external_context_reference
        (tenant_record_id, reference_authority_code, external_object_kind_code);

CREATE INDEX application_context_projection_lookup_index
    ON architecture_core.application_context_projection
        (tenant_record_id, application_object_id, valid_from DESC)
    WHERE superseded_at IS NULL;

CREATE FUNCTION architecture_core.project_application_context_impact(
    requested_application_object_id uuid,
    assessment_valid_at timestamptz,
    assessment_recorded_at timestamptz
)
RETURNS TABLE (
    application_object_id uuid,
    external_context_reference_id uuid,
    reference_authority_code text,
    canonical_object_uri text,
    external_object_kind_code text,
    projection_relation_code text,
    truth_status_code text,
    projection_receipt_id uuid,
    projection_source_code text,
    event_source_uri text,
    event_identifier text,
    payload_sha256 text,
    valid_from timestamptz,
    valid_to timestamptz,
    recorded_at timestamptz,
    evidence_state_code text,
    recommended_action_code text
)
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
  application_type_code text;
BEGIN
  IF requested_application_object_id IS NULL
     OR assessment_valid_at IS NULL
     OR assessment_recorded_at IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'application and valid/system cutoffs are required';
  END IF;

  SELECT object_type.object_type_code
    INTO application_type_code
    FROM architecture_core.architecture_object AS architecture_object
    JOIN architecture_core.object_type AS object_type
      ON object_type.object_type_id = architecture_object.object_type_id
   WHERE architecture_object.tenant_record_id =
         architecture_core.current_tenant_id()
     AND architecture_object.architecture_object_id =
         requested_application_object_id;

  IF application_type_code IS DISTINCT FROM 'application_record' THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'application is unavailable for the active tenant';
  END IF;

  RETURN QUERY
  SELECT
      application_context_projection.application_object_id,
      external_context_reference.external_context_reference_id,
      external_context_reference.reference_authority_code,
      external_context_reference.canonical_object_uri,
      external_context_reference.external_object_kind_code,
      application_context_projection.projection_relation_code,
      application_context_projection.truth_status_code,
      projection_receipt.projection_receipt_id,
      split_part(projection_receipt.event_source_uri, ':', 4)::text,
      projection_receipt.event_source_uri,
      projection_receipt.event_identifier,
      projection_receipt.payload_sha256,
      application_context_projection.valid_from,
      application_context_projection.valid_to,
      application_context_projection.recorded_at,
      CASE
        WHEN application_context_projection.truth_status_code IN
             ('inferred', 'proposed')
          THEN 'requires_truth_review'
        ELSE 'complete'
      END::text,
      CASE
        WHEN application_context_projection.truth_status_code IN
             ('inferred', 'proposed')
          THEN 'review_truth_origin'
        WHEN external_context_reference.external_object_kind_code =
             'database_schema'
          THEN 'review_schema_dependency'
        WHEN external_context_reference.external_object_kind_code =
             'data_product'
          THEN 'review_data_product_impact'
        WHEN external_context_reference.external_object_kind_code =
             'dashboard'
          THEN 'review_dashboard_impact'
        WHEN external_context_reference.external_object_kind_code =
             'model'
          THEN 'review_model_impact'
        WHEN external_context_reference.external_object_kind_code =
             'ai_agent'
          THEN 'review_ai_agent_impact'
        ELSE 'review_external_impact'
      END::text
    FROM architecture_core.application_context_projection
    JOIN architecture_core.external_context_reference
      ON external_context_reference.tenant_record_id =
         application_context_projection.tenant_record_id
     AND external_context_reference.external_context_reference_id =
         application_context_projection.external_context_reference_id
    JOIN architecture_core.projection_receipt
      ON projection_receipt.tenant_record_id =
         application_context_projection.tenant_record_id
     AND projection_receipt.projection_receipt_id =
         application_context_projection.projection_receipt_id
   WHERE application_context_projection.tenant_record_id =
         architecture_core.current_tenant_id()
     AND application_context_projection.application_object_id =
         requested_application_object_id
     AND application_context_projection.valid_from <= assessment_valid_at
     AND (
        application_context_projection.valid_to IS NULL
        OR application_context_projection.valid_to > assessment_valid_at
     )
     AND application_context_projection.recorded_at <= assessment_recorded_at
     AND (
        application_context_projection.superseded_at IS NULL
        OR application_context_projection.superseded_at >
           assessment_recorded_at
     )
     AND application_context_projection.truth_status_code NOT IN
         ('superseded', 'rejected')
     AND projection_receipt.processing_status_code = 'processed'
     AND projection_receipt.processed_at IS NOT NULL
     AND projection_receipt.processed_at <= assessment_recorded_at
   ORDER BY
      external_context_reference.external_object_kind_code,
      external_context_reference.canonical_object_uri,
      application_context_projection.application_context_projection_id;
END;
$$;

COMMENT ON FUNCTION architecture_core.project_application_context_impact(
    uuid,
    timestamptz,
    timestamptz
) IS
'Projects receipt-bound cross-domain references for one tenant-scoped EA application at independent valid/system cutoffs. The function preserves foreign authority, source event identity, payload digest, and truth origin; inferred/proposed evidence stays review-only and no foreign application tables are queried.';

COMMIT;
