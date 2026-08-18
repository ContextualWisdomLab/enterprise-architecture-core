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

COMMENT ON FUNCTION architecture_core.bind_data_management_milestone_causation() IS
'Binds the transactional outbox causation UUIDv7 into privacy-minimized milestone-completion event data so the executable publisher payload matches the AsyncAPI contract.';

COMMIT;
