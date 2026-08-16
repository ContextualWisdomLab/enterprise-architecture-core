BEGIN;

ALTER TABLE architecture_core.object_revision
    DROP CONSTRAINT object_revision_active_interval_exclusion;
ALTER TABLE architecture_core.object_revision
    ADD CONSTRAINT object_revision_active_interval_exclusion
    EXCLUDE USING gist (
        tenant_record_id WITH =,
        architecture_object_id WITH =,
        tstzrange(valid_from, valid_to, '[)') WITH &&
    ) WHERE (
        superseded_at IS NULL
        AND truth_status_code = 'authoritative'
    );

ALTER TABLE architecture_core.architecture_relation
    DROP CONSTRAINT architecture_relation_active_interval_exclusion;
ALTER TABLE architecture_core.architecture_relation
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
