BEGIN;

-- The original receipt shape stored local compatibility labels in fields named
-- as CGC profile/admission versions. Preserve only the exact previously emitted
-- candidate labels, then normalize them to the identity actually exported by
-- ContextAssertionAdmission. Any unknown candidate value fails closed instead
-- of being reinterpreted as released contract evidence.
ALTER TABLE architecture_core.context_assertion_projection_receipt
    DROP CONSTRAINT context_assertion_projection_receipt_profile_version;
ALTER TABLE architecture_core.context_assertion_projection_receipt
    DROP CONSTRAINT context_assertion_projection_receipt_admission_version;

ALTER TABLE architecture_core.context_assertion_projection_receipt
    RENAME COLUMN context_profile_version TO context_profile_id;

DO $$
BEGIN
  IF EXISTS (
      SELECT 1
        FROM architecture_core.context_assertion_projection_receipt
       WHERE context_profile_id IS DISTINCT FROM 'context-assertion/v1'
          OR admission_version IS DISTINCT FROM 'context-fabric-admission/v1'
  ) THEN
    RAISE EXCEPTION
      'unknown provisional Context Assertion admission identity cannot be migrated';
  END IF;
END;
$$;

ALTER TABLE architecture_core.context_assertion_projection_receipt
    ADD COLUMN context_profile_version integer;

UPDATE architecture_core.context_assertion_projection_receipt
   SET context_profile_id =
         'urn:cwl:context-contracts:context-assertion-event-semantics:v1',
       context_profile_version = 1,
       admission_version = '1';

ALTER TABLE architecture_core.context_assertion_projection_receipt
    ALTER COLUMN context_profile_version SET NOT NULL;
ALTER TABLE architecture_core.context_assertion_projection_receipt
    ALTER COLUMN admission_version TYPE integer
    USING admission_version::integer;

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
