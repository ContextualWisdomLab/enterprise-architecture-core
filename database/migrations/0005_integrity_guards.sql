BEGIN;

CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE architecture_core.tenant_record
    ADD CONSTRAINT tenant_record_code_format
    CHECK (tenant_code ~ '^[a-z][a-z0-9_]{1,62}$'),
    ADD CONSTRAINT tenant_record_uuid_version
    CHECK (uuid_extract_version(tenant_record_id) = 7);

ALTER TABLE architecture_core.evidence_record
    ADD CONSTRAINT evidence_record_uuid_version
    CHECK (uuid_extract_version(evidence_record_id) = 7);

ALTER TABLE architecture_core.identity_link
    ADD CONSTRAINT identity_link_uuid_version
    CHECK (uuid_extract_version(identity_link_id) = 7),
    ADD CONSTRAINT identity_link_active_interval_exclusion
    EXCLUDE USING gist (
        tenant_record_id WITH =,
        keyverse_subject_id WITH =,
        tstzrange(valid_from, valid_to, '[)') WITH &&
    ) WHERE (superseded_at IS NULL);

ALTER TABLE architecture_core.object_type
    ADD CONSTRAINT object_type_uuid_version
    CHECK (uuid_extract_version(object_type_id) = 7);

ALTER TABLE architecture_core.architecture_object
    ADD CONSTRAINT architecture_object_uuid_version
    CHECK (uuid_extract_version(architecture_object_id) = 7);

ALTER TABLE architecture_core.object_revision
    ADD CONSTRAINT object_revision_uuid_version
    CHECK (uuid_extract_version(object_revision_id) = 7),
    ADD CONSTRAINT object_revision_active_interval_exclusion
    EXCLUDE USING gist (
        tenant_record_id WITH =,
        architecture_object_id WITH =,
        tstzrange(valid_from, valid_to, '[)') WITH &&
    ) WHERE (
        superseded_at IS NULL
        AND truth_status_code = 'authoritative'
    );

ALTER TABLE architecture_core.relation_type
    ADD CONSTRAINT relation_type_uuid_version
    CHECK (uuid_extract_version(relation_type_id) = 7);

ALTER TABLE architecture_core.architecture_relation
    ADD CONSTRAINT architecture_relation_uuid_version
    CHECK (uuid_extract_version(architecture_relation_id) = 7),
    ADD CONSTRAINT architecture_relation_active_interval_exclusion
    EXCLUDE USING gist (
        tenant_record_id WITH =,
        relation_type_id WITH =,
        source_object_id WITH =,
        target_object_id WITH =,
        tstzrange(valid_from, valid_to, '[)') WITH &&
    ) WHERE (
        superseded_at IS NULL
        AND truth_status_code = 'authoritative'
    );

ALTER TABLE architecture_core.lifecycle_phase
    ADD CONSTRAINT lifecycle_phase_uuid_version
    CHECK (uuid_extract_version(lifecycle_phase_id) = 7);

ALTER TABLE architecture_core.lifecycle_interval
    ADD CONSTRAINT lifecycle_interval_uuid_version
    CHECK (uuid_extract_version(lifecycle_interval_id) = 7),
    ADD CONSTRAINT lifecycle_interval_active_interval_exclusion
    EXCLUDE USING gist (
        tenant_record_id WITH =,
        architecture_object_id WITH =,
        tstzrange(valid_from, valid_to, '[)') WITH &&
    ) WHERE (superseded_at IS NULL);

ALTER TABLE architecture_core.outbox_event
    ADD CONSTRAINT outbox_event_uuid_version
    CHECK (uuid_extract_version(outbox_event_id) = 7),
    ADD CONSTRAINT outbox_event_correlation_uuid_version
    CHECK (
        correlation_event_id IS NULL
        OR uuid_extract_version(correlation_event_id) = 7
    ),
    ADD CONSTRAINT outbox_event_causation_uuid_version
    CHECK (
        causation_event_id IS NULL
        OR uuid_extract_version(causation_event_id) = 7
    ),
    ADD CONSTRAINT outbox_event_payload_object
    CHECK (jsonb_typeof(event_payload_json) = 'object');

ALTER TABLE architecture_core.projection_receipt
    ADD CONSTRAINT projection_receipt_uuid_version
    CHECK (uuid_extract_version(projection_receipt_id) = 7),
    ADD CONSTRAINT projection_receipt_source_format
    CHECK (
        event_source_uri ~
        '^urn:cwl:[a-z][a-z0-9_]{1,62}:[a-z][a-z0-9_]{1,62}$'
    ),
    ADD CONSTRAINT projection_receipt_identifier_format
    CHECK (
        event_identifier ~
        '^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
    );

CREATE FUNCTION architecture_core.validate_architecture_object_identity()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  tenant_code_value text;
  object_type_code_value text;
  expected_asset_uri text;
BEGIN
  SELECT tenant_code
    INTO tenant_code_value
    FROM architecture_core.tenant_record
   WHERE tenant_record_id = NEW.tenant_record_id;
  SELECT object_type_code
    INTO object_type_code_value
    FROM architecture_core.object_type
   WHERE object_type_id = NEW.object_type_id;
  IF tenant_code_value IS NULL OR object_type_code_value IS NULL THEN
    RETURN NEW;
  END IF;
  expected_asset_uri := format(
      'urn:cwl:%s:ea_core:%s:%s',
      tenant_code_value,
      object_type_code_value,
      NEW.architecture_object_id
  );
  IF NEW.canonical_asset_uri <> expected_asset_uri THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'canonical_asset_uri does not match tenant, type, and object id';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER architecture_object_identity_guard
BEFORE INSERT OR UPDATE OF
    tenant_record_id,
    architecture_object_id,
    object_type_id,
    canonical_asset_uri
ON architecture_core.architecture_object
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_architecture_object_identity();

CREATE FUNCTION architecture_core.validate_architecture_relation_types()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  expected_source_type_id uuid;
  expected_target_type_id uuid;
  actual_source_type_id uuid;
  actual_target_type_id uuid;
BEGIN
  SELECT source_type_id, target_type_id
    INTO expected_source_type_id, expected_target_type_id
    FROM architecture_core.relation_type
   WHERE relation_type_id = NEW.relation_type_id;
  SELECT object_type_id
    INTO actual_source_type_id
    FROM architecture_core.architecture_object
   WHERE tenant_record_id = NEW.tenant_record_id
     AND architecture_object_id = NEW.source_object_id;
  SELECT object_type_id
    INTO actual_target_type_id
    FROM architecture_core.architecture_object
   WHERE tenant_record_id = NEW.tenant_record_id
     AND architecture_object_id = NEW.target_object_id;
  IF expected_source_type_id IS NOT NULL
     AND actual_source_type_id IS DISTINCT FROM expected_source_type_id THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'relation source object type is not allowed';
  END IF;
  IF expected_target_type_id IS NOT NULL
     AND actual_target_type_id IS DISTINCT FROM expected_target_type_id THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'relation target object type is not allowed';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER architecture_relation_type_guard
BEFORE INSERT OR UPDATE OF
    tenant_record_id,
    relation_type_id,
    source_object_id,
    target_object_id
ON architecture_core.architecture_relation
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_architecture_relation_types();

CREATE FUNCTION architecture_core.validate_typed_extension_object_type()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  actual_object_type_code text;
  expected_object_type_code text := TG_ARGV[0];
BEGIN
  SELECT object_type.object_type_code
    INTO actual_object_type_code
    FROM architecture_core.architecture_object AS architecture_object
    JOIN architecture_core.object_type AS object_type
      ON object_type.object_type_id = architecture_object.object_type_id
   WHERE architecture_object.tenant_record_id = NEW.tenant_record_id
     AND architecture_object.architecture_object_id = NEW.architecture_object_id;
  IF actual_object_type_code IS NOT NULL
     AND actual_object_type_code IS DISTINCT FROM expected_object_type_code THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = format(
          'typed extension expects %s but object is %s',
          expected_object_type_code,
          actual_object_type_code
      );
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER business_capability_type_guard
BEFORE INSERT OR UPDATE OF tenant_record_id, architecture_object_id
ON architecture_core.business_capability
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_typed_extension_object_type(
    'business_capability'
);

CREATE TRIGGER organization_unit_type_guard
BEFORE INSERT OR UPDATE OF tenant_record_id, architecture_object_id
ON architecture_core.organization_unit
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_typed_extension_object_type(
    'organization_unit'
);

CREATE TRIGGER application_record_type_guard
BEFORE INSERT OR UPDATE OF tenant_record_id, architecture_object_id
ON architecture_core.application_record
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_typed_extension_object_type(
    'application_record'
);

CREATE TRIGGER application_interface_type_guard
BEFORE INSERT OR UPDATE OF tenant_record_id, architecture_object_id
ON architecture_core.application_interface
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_typed_extension_object_type(
    'application_interface'
);

CREATE TRIGGER technology_provider_type_guard
BEFORE INSERT OR UPDATE OF tenant_record_id, architecture_object_id
ON architecture_core.technology_provider
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_typed_extension_object_type(
    'technology_provider'
);

CREATE TRIGGER technology_component_type_guard
BEFORE INSERT OR UPDATE OF tenant_record_id, architecture_object_id
ON architecture_core.technology_component
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_typed_extension_object_type(
    'technology_component'
);

CREATE TRIGGER technology_version_type_guard
BEFORE INSERT OR UPDATE OF tenant_record_id, architecture_object_id
ON architecture_core.technology_version
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_typed_extension_object_type(
    'technology_version'
);

COMMIT;
