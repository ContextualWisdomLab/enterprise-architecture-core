BEGIN;

ALTER TABLE architecture_core.projection_receipt
    ADD CONSTRAINT projection_receipt_source_uri_format
    CHECK (
        event_source_uri ~
        '^urn:cwl:(?=[^:]{2,63}:)[a-z][a-z0-9]+(?:_[a-z0-9]+)*:(?=[^:]{2,63}$)[a-z][a-z0-9]+(?:_[a-z0-9]+)*$'
    );

DO $$
BEGIN
  IF EXISTS (
      SELECT 1
        FROM architecture_core.projection_receipt AS projection_receipt
        JOIN architecture_core.tenant_record AS tenant_record
          ON tenant_record.tenant_record_id = projection_receipt.tenant_record_id
       WHERE split_part(projection_receipt.event_source_uri, ':', 3)
             IS DISTINCT FROM tenant_record.tenant_code
  ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE =
        'existing projection receipt source tenant does not match row tenant';
  END IF;
END;
$$;

CREATE FUNCTION architecture_core.validate_projection_receipt_source_uri()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  expected_tenant_code text;
  source_tenant_code text;
BEGIN
  SELECT tenant_record.tenant_code
    INTO expected_tenant_code
    FROM architecture_core.tenant_record AS tenant_record
   WHERE tenant_record.tenant_record_id = NEW.tenant_record_id;

  source_tenant_code := split_part(NEW.event_source_uri, ':', 3);

  IF expected_tenant_code IS NULL
     OR source_tenant_code IS DISTINCT FROM expected_tenant_code THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'projection receipt source tenant does not match row tenant';
  END IF;

  RETURN NEW;
END;
$$;

COMMENT ON FUNCTION architecture_core.validate_projection_receipt_source_uri()
IS 'Rejects a projection receipt unless its canonical Context Fabric source URI names the same tenant that owns the receipt row.';

CREATE TRIGGER projection_receipt_source_tenant_guard
BEFORE INSERT OR UPDATE
ON architecture_core.projection_receipt
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_projection_receipt_source_uri();

COMMIT;
