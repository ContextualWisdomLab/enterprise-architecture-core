BEGIN;

-- A dataschema URI identifies the schema resource but does not prove which
-- admission receipt version produced an existing projection row. If a database
-- was paused on the provisional candidate migration, require re-admission rather
-- than fabricating schema-version evidence during DDL upgrade.
DO $$
BEGIN
  IF EXISTS (
      SELECT 1
        FROM architecture_core.context_assertion_projection_receipt
  ) THEN
    RAISE EXCEPTION
      'provisional Context Assertion receipts require re-admission before exact schema-version identity can be recorded';
  END IF;
END;
$$;

ALTER TABLE architecture_core.context_assertion_projection_receipt
    ADD COLUMN context_schema_version integer NOT NULL;

ALTER TABLE architecture_core.context_assertion_projection_receipt
    ADD CONSTRAINT context_assertion_projection_receipt_schema_version
        CHECK (context_schema_version = 1);

COMMENT ON COLUMN architecture_core.context_assertion_projection_receipt.context_schema_version IS
'Exact Context Assertion schema version copied from the admitted CGC ContextAssertionAdmission receipt; consumers must not infer it from dataschema text.';

COMMIT;
