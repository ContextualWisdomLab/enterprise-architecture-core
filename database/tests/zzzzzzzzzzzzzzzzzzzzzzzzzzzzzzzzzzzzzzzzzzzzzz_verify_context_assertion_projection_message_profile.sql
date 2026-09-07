\set ON_ERROR_STOP on

-- Projection receipts must preserve the separately versioned structured-message
-- admission profile exported by the released CGC ContextAssertionAdmission
-- surface. The event-semantics profile alone cannot prove transport admission.
DO $$
DECLARE
  message_profile_id_type text;
  message_profile_version_type text;
  message_profile_id_constraint text;
  message_profile_version_constraint text;
BEGIN
  SELECT data_type
    INTO message_profile_id_type
    FROM information_schema.columns
   WHERE table_schema = 'architecture_core'
     AND table_name = 'context_assertion_projection_receipt'
     AND column_name = 'message_profile_id';

  SELECT data_type
    INTO message_profile_version_type
    FROM information_schema.columns
   WHERE table_schema = 'architecture_core'
     AND table_name = 'context_assertion_projection_receipt'
     AND column_name = 'message_profile_version';

  IF message_profile_id_type IS DISTINCT FROM 'text'
     OR message_profile_version_type IS DISTINCT FROM 'integer' THEN
    RAISE EXCEPTION
      'Context Assertion receipt does not preserve exact CGC message-admission profile identity';
  END IF;

  SELECT pg_get_constraintdef(oid)
    INTO message_profile_id_constraint
    FROM pg_constraint
   WHERE conrelid =
         'architecture_core.context_assertion_projection_receipt'::regclass
     AND conname = 'context_assertion_projection_receipt_message_profile_id';

  SELECT pg_get_constraintdef(oid)
    INTO message_profile_version_constraint
    FROM pg_constraint
   WHERE conrelid =
         'architecture_core.context_assertion_projection_receipt'::regclass
     AND conname = 'context_assertion_projection_receipt_message_profile_version';

  IF message_profile_id_constraint IS NULL
     OR position(
          'urn:cwl:context-contracts:context-assertion-message-admission:v1'
          IN message_profile_id_constraint
        ) = 0
     OR message_profile_version_constraint IS NULL
     OR position(
          'message_profile_version = 1'
          IN message_profile_version_constraint
        ) = 0 THEN
    RAISE EXCEPTION
      'Context Assertion receipt constraints do not bind exact CGC message-admission profile identity';
  END IF;
END;
$$;
