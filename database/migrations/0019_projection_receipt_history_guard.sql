BEGIN;

CREATE FUNCTION architecture_core.guard_projection_receipt_history()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'projection receipt history cannot be hard-deleted';
  END IF;

  IF NEW.tenant_record_id IS DISTINCT FROM OLD.tenant_record_id
     OR NEW.projection_receipt_id IS DISTINCT FROM OLD.projection_receipt_id
     OR NEW.event_source_uri IS DISTINCT FROM OLD.event_source_uri
     OR NEW.event_identifier IS DISTINCT FROM OLD.event_identifier
     OR NEW.payload_sha256 IS DISTINCT FROM OLD.payload_sha256
     OR NEW.schema_version IS DISTINCT FROM OLD.schema_version
     OR NEW.received_at IS DISTINCT FROM OLD.received_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'projection receipt evidence identity is immutable';
  END IF;

  IF OLD.processing_status_code IN ('processed', 'rejected')
     AND NEW IS DISTINCT FROM OLD THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'terminal projection receipt evidence is immutable';
  END IF;

  IF OLD.processing_status_code <> 'received'
     AND NEW.processing_status_code = 'received' THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE =
        'projection receipt cannot return to received after processing begins';
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER projection_receipt_history_guard
BEFORE UPDATE OR DELETE
ON architecture_core.projection_receipt
FOR EACH ROW
EXECUTE FUNCTION architecture_core.guard_projection_receipt_history();

COMMIT;
