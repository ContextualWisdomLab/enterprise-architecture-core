\set ON_ERROR_STOP on

-- The connector ACL promises to retain schema, profile, and admission versions.
-- Persist the schema version explicitly rather than inferring it later from a
-- dataschema URI whose parsing rules belong to the upstream Shared Kernel.
DO $$
DECLARE
  schema_version_type text;
  schema_version_default text;
  schema_version_constraint text;
BEGIN
  SELECT data_type, column_default
    INTO schema_version_type, schema_version_default
    FROM information_schema.columns
   WHERE table_schema = 'architecture_core'
     AND table_name = 'context_assertion_projection_receipt'
     AND column_name = 'context_schema_version';

  IF schema_version_type IS DISTINCT FROM 'integer' THEN
    RAISE EXCEPTION
      'Context Assertion receipt does not retain the CGC schema version';
  END IF;

  IF schema_version_default IS NOT NULL THEN
    RAISE EXCEPTION
      'future Context Assertion receipts must supply the admitted schema version';
  END IF;

  SELECT pg_get_constraintdef(oid)
    INTO schema_version_constraint
    FROM pg_constraint
   WHERE conrelid =
         'architecture_core.context_assertion_projection_receipt'::regclass
     AND conname = 'context_assertion_projection_receipt_schema_version';

  IF schema_version_constraint IS NULL
     OR position('context_schema_version = 1' IN schema_version_constraint) = 0 THEN
    RAISE EXCEPTION
      'Context Assertion receipt schema version is not bound to CGC v1';
  END IF;
END;
$$;
