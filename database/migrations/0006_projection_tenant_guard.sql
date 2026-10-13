BEGIN;

CREATE FUNCTION architecture_core.validate_projection_receipt_tenant()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  expected_tenant_code text;
  source_tenant_code text;
BEGIN
  SELECT tenant_code
    INTO expected_tenant_code
    FROM architecture_core.tenant_record
   WHERE tenant_record_id = NEW.tenant_record_id;

  source_tenant_code := split_part(NEW.event_source_uri, ':', 3);
  IF expected_tenant_code IS NULL
     OR source_tenant_code IS DISTINCT FROM expected_tenant_code THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'projection receipt event source tenant does not match row tenant';
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER projection_receipt_tenant_guard
BEFORE INSERT OR UPDATE OF tenant_record_id, event_source_uri
ON architecture_core.projection_receipt
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_projection_receipt_tenant();

COMMIT;
