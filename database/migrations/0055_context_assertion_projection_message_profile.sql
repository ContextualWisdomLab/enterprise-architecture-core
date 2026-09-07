BEGIN;

-- A Context Assertion projection receipt already proves the outer structured
-- CloudEvent media type and the v1 event-semantics profile. The released CGC
-- admission surface now carries a second, separately versioned identity for the
-- structured-message admission profile. Retain that identity explicitly rather
-- than inferring transport admission from the event profile or media type.
--
-- All rows reachable at this migration point are constrained to the sole v1
-- structured CloudEvent shape introduced by migrations 0051-0054. Backfill that
-- known v1 message-profile identity with constant ADD COLUMN defaults, then
-- remove the defaults so every future receipt must copy the exact values
-- returned by ContextAssertionAdmission. This avoids UPDATEs while the immutable
-- history trigger remains enabled.
ALTER TABLE architecture_core.context_assertion_projection_receipt
    ADD COLUMN message_profile_id text NOT NULL DEFAULT
        'urn:cwl:context-contracts:context-assertion-message-admission:v1',
    ADD COLUMN message_profile_version integer NOT NULL DEFAULT 1;

ALTER TABLE architecture_core.context_assertion_projection_receipt
    ALTER COLUMN message_profile_id DROP DEFAULT,
    ALTER COLUMN message_profile_version DROP DEFAULT;

ALTER TABLE architecture_core.context_assertion_projection_receipt
    ADD CONSTRAINT context_assertion_projection_receipt_message_profile_id
        CHECK (
            message_profile_id =
            'urn:cwl:context-contracts:context-assertion-message-admission:v1'
        ),
    ADD CONSTRAINT context_assertion_projection_receipt_message_profile_version
        CHECK (message_profile_version = 1);

COMMENT ON COLUMN architecture_core.context_assertion_projection_receipt.message_profile_id IS
'Exact structured-message admission profile id retained from the admitted CGC ContextAssertionAdmission receipt; it must not be inferred from transport media type or event profile.';
COMMENT ON COLUMN architecture_core.context_assertion_projection_receipt.message_profile_version IS
'Exact structured-message admission profile version retained from the admitted CGC ContextAssertionAdmission receipt.';

COMMIT;
