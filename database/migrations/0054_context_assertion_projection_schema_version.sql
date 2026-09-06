BEGIN;

-- Every pre-existing Context Assertion receipt is already constrained to the v1
-- dataschema by migration 0051. Backfill that known identity without rewriting
-- immutable history, then remove the default so new receipts must copy the exact
-- schema_version returned by the admitted CGC SDK receipt.
ALTER TABLE architecture_core.context_assertion_projection_receipt
    ADD COLUMN context_schema_version integer NOT NULL DEFAULT 1;

ALTER TABLE architecture_core.context_assertion_projection_receipt
    ALTER COLUMN context_schema_version DROP DEFAULT;

ALTER TABLE architecture_core.context_assertion_projection_receipt
    ADD CONSTRAINT context_assertion_projection_receipt_schema_version
        CHECK (context_schema_version = 1);

COMMENT ON COLUMN architecture_core.context_assertion_projection_receipt.context_schema_version IS
'Exact Context Assertion schema version retained from the admitted CGC ContextAssertionAdmission receipt; consumers must not infer it from dataschema text.';

COMMIT;
