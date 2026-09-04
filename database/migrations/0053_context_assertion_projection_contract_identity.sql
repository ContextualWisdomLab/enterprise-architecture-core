BEGIN;

-- The original receipt shape stored local compatibility labels in fields named
-- as CGC profile/admission versions. Preserve only the exact previously emitted
-- candidate labels, then replace them with the identity actually exported by
-- ContextAssertionAdmission. Any unknown candidate value fails closed instead
-- of being reinterpreted as released contract evidence.
ALTER TABLE architecture_core.context_assertion_projection_receipt
    DROP CONSTRAINT context_assertion_projection_receipt_profile_version;
ALTER TABLE architecture_core.context_assertion_projection_receipt
    DROP CONSTRAINT context_assertion_projection_receipt_admission_version;

ALTER TABLE architecture_core.context_assertion_projection_receipt
    RENAME COLUMN context_profile_version TO legacy_context_profile_label;
ALTER TABLE architecture_core.context_assertion_projection_receipt
    RENAME COLUMN admission_version TO legacy_admission_label;

DO $$
BEGIN
  IF EXISTS (
      SELECT 1
        FROM architecture_core.context_assertion_projection_receipt
       WHERE legacy_context_profile_label IS DISTINCT FROM 'context-assertion/v1'
          OR legacy_admission_label IS DISTINCT FROM 'context-fabric-admission/v1'
  ) THEN
    RAISE EXCEPTION
      'unknown provisional Context Assertion admission identity cannot be migrated';
  END IF;
END;
$$;

-- Constant ADD COLUMN defaults backfill the exact v1 identity without issuing
-- row UPDATE statements, so the immutable receipt-history trigger stays enabled
-- for the entire migration. Defaults are removed immediately because future
-- inserts must supply the identity returned by the admitted CGC SDK receipt.
ALTER TABLE architecture_core.context_assertion_projection_receipt
    ADD COLUMN context_profile_id text NOT NULL DEFAULT
        'urn:cwl:context-contracts:context-assertion-event-semantics:v1',
    ADD COLUMN context_profile_version integer NOT NULL DEFAULT 1,
    ADD COLUMN admission_version integer NOT NULL DEFAULT 1;

ALTER TABLE architecture_core.context_assertion_projection_receipt
    ALTER COLUMN context_profile_id DROP DEFAULT,
    ALTER COLUMN context_profile_version DROP DEFAULT,
    ALTER COLUMN admission_version DROP DEFAULT;

ALTER TABLE architecture_core.context_assertion_projection_receipt
    DROP COLUMN legacy_context_profile_label,
    DROP COLUMN legacy_admission_label;

ALTER TABLE architecture_core.context_assertion_projection_receipt
    ADD CONSTRAINT context_assertion_projection_receipt_profile_id
        CHECK (
            context_profile_id =
            'urn:cwl:context-contracts:context-assertion-event-semantics:v1'
        ),
    ADD CONSTRAINT context_assertion_projection_receipt_profile_version
        CHECK (context_profile_version = 1),
    ADD CONSTRAINT context_assertion_projection_receipt_admission_version
        CHECK (admission_version = 1);

COMMENT ON COLUMN architecture_core.context_assertion_projection_receipt.context_profile_id IS
'Exact semantic profile id retained from the admitted CGC ContextAssertionAdmission receipt.';
COMMENT ON COLUMN architecture_core.context_assertion_projection_receipt.context_profile_version IS
'Exact semantic profile version retained from the admitted CGC ContextAssertionAdmission receipt.';
COMMENT ON COLUMN architecture_core.context_assertion_projection_receipt.admission_version IS
'Exact admission implementation version retained from the admitted CGC ContextAssertionAdmission receipt.';

COMMIT;
