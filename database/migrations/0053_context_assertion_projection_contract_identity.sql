BEGIN;

-- The provisional receipt shape stored local compatibility labels rather than
-- the exact CGC profile/admission identity returned by ContextAssertionAdmission.
-- Those labels are insufficient evidence to promote an existing row to an exact
-- released-contract receipt. Fail closed instead of manufacturing provenance.
DO $$
BEGIN
  IF EXISTS (
      SELECT 1
        FROM architecture_core.context_assertion_projection_receipt
  ) THEN
    RAISE EXCEPTION
      'provisional Context Assertion receipts require re-admission before exact profile/admission identity can be recorded';
  END IF;
END;
$$;

ALTER TABLE architecture_core.context_assertion_projection_receipt
    DROP CONSTRAINT context_assertion_projection_receipt_profile_version;
ALTER TABLE architecture_core.context_assertion_projection_receipt
    DROP CONSTRAINT context_assertion_projection_receipt_admission_version;

ALTER TABLE architecture_core.context_assertion_projection_receipt
    RENAME COLUMN context_profile_version TO legacy_context_profile_label;
ALTER TABLE architecture_core.context_assertion_projection_receipt
    RENAME COLUMN admission_version TO legacy_admission_label;

-- The table is proven empty above. New rows must supply identity copied from the
-- admitted CGC SDK receipt; no DDL default may turn an unknown historical value
-- into exact contract evidence.
ALTER TABLE architecture_core.context_assertion_projection_receipt
    ADD COLUMN context_profile_id text NOT NULL,
    ADD COLUMN context_profile_version integer NOT NULL,
    ADD COLUMN admission_version integer NOT NULL;

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
'Exact semantic profile id copied from the admitted CGC ContextAssertionAdmission receipt; provisional rows must be re-admitted rather than inferred.';
COMMENT ON COLUMN architecture_core.context_assertion_projection_receipt.context_profile_version IS
'Exact semantic profile version copied from the admitted CGC ContextAssertionAdmission receipt; provisional rows must be re-admitted rather than inferred.';
COMMENT ON COLUMN architecture_core.context_assertion_projection_receipt.admission_version IS
'Exact admission implementation version copied from the admitted CGC ContextAssertionAdmission receipt; provisional rows must be re-admitted rather than inferred.';

COMMIT;
