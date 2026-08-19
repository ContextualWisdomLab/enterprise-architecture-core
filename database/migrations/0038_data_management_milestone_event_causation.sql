BEGIN;

CREATE FUNCTION architecture_core.bind_data_management_milestone_causation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
  IF NEW.event_type_code =
     'org.contextualwisdomlab.ea.data_management.milestone_completed.v1' THEN
    IF NEW.causation_event_id IS NULL THEN
      RAISE EXCEPTION USING
        ERRCODE = '23514',
        MESSAGE = 'data-management milestone completion requires a causation event';
    END IF;
    NEW.event_payload_json := pg_catalog.jsonb_set(
      NEW.event_payload_json,
      '{causation_event_id}',
      pg_catalog.to_jsonb(NEW.causation_event_id::text),
      true
    );
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER data_management_milestone_causation_guard
BEFORE INSERT
ON architecture_core.outbox_event
FOR EACH ROW
EXECUTE FUNCTION architecture_core.bind_data_management_milestone_causation();

CREATE FUNCTION architecture_core.serialize_data_management_evidence_acceptance()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
DECLARE
  assessment_projection_id uuid;
BEGIN
  SELECT plan_record.data_management_assessment_projection_id
    INTO assessment_projection_id
    FROM architecture_core.assessment_improvement_plan AS plan_record
   WHERE plan_record.tenant_record_id = NEW.tenant_record_id
     AND plan_record.assessment_improvement_plan_id =
         NEW.assessment_improvement_plan_id;

  IF assessment_projection_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'evidence acceptance requires a tenant-local assessment improvement plan';
  END IF;

  PERFORM 1
    FROM architecture_core.data_management_assessment_projection AS projection_record
   WHERE projection_record.tenant_record_id = NEW.tenant_record_id
     AND projection_record.data_management_assessment_projection_id =
         assessment_projection_id
   FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'evidence acceptance requires a tenant-local assessment projection';
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER data_management_evidence_acceptance_serialization_guard
BEFORE INSERT
ON architecture_core.assessment_evidence_acceptance
FOR EACH ROW
EXECUTE FUNCTION architecture_core.serialize_data_management_evidence_acceptance();

COMMENT ON FUNCTION architecture_core.bind_data_management_milestone_causation() IS
'Binds the transactional outbox causation UUIDv7 into privacy-minimized milestone-completion event data so the executable publisher payload matches the AsyncAPI contract.';

COMMENT ON FUNCTION architecture_core.serialize_data_management_evidence_acceptance() IS
'Serializes evidence acceptance on the tenant-local assessment projection row before insertion so concurrent closures of different gaps cannot both decide against stale uncommitted acceptance state.';

COMMIT;
