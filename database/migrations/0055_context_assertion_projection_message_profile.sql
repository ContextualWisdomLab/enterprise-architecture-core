BEGIN;

-- The structured CloudEvent media type and event-semantics profile do not prove
-- which separately versioned message-admission profile admitted an existing row.
-- If a database was paused on the provisional candidate migration, fail closed
-- and require re-admission instead of manufacturing message-profile provenance.
DO $$
BEGIN
  IF EXISTS (
      SELECT 1
        FROM architecture_core.context_assertion_projection_receipt
  ) THEN
    RAISE EXCEPTION
      'provisional Context Assertion receipts require re-admission before exact message-profile identity can be recorded';
  END IF;
END;
$$;

ALTER TABLE architecture_core.context_assertion_projection_receipt
    ADD COLUMN message_profile_id text NOT NULL,
    ADD COLUMN message_profile_version integer NOT NULL;

ALTER TABLE architecture_core.context_assertion_projection_receipt
    ADD CONSTRAINT context_assertion_projection_receipt_message_profile_id
        CHECK (
            message_profile_id =
            'urn:cwl:context-contracts:context-assertion-message-admission:v1'
        ),
    ADD CONSTRAINT context_assertion_projection_receipt_message_profile_version
        CHECK (message_profile_version = 1);

COMMENT ON COLUMN architecture_core.context_assertion_projection_receipt.message_profile_id IS
'Exact structured-message admission profile id copied from the admitted CGC ContextAssertionAdmission receipt; it must not be inferred from transport media type or event profile.';
COMMENT ON COLUMN architecture_core.context_assertion_projection_receipt.message_profile_version IS
'Exact structured-message admission profile version copied from the admitted CGC ContextAssertionAdmission receipt; provisional rows must be re-admitted rather than inferred.';

COMMIT;
