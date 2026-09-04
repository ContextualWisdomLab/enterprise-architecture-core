\set ON_ERROR_STOP on

-- Projection receipts must preserve the exact identity exported by the released
-- CGC ContextAssertionAdmission surface. A local compatibility label is not a
-- substitute for the semantic profile id/version or admission version.
DO $$
DECLARE
  profile_id_type text;
  profile_version_type text;
  admission_version_type text;
BEGIN
  SELECT data_type
    INTO profile_id_type
    FROM information_schema.columns
   WHERE table_schema = 'architecture_core'
     AND table_name = 'context_assertion_projection_receipt'
     AND column_name = 'context_profile_id';

  SELECT data_type
    INTO profile_version_type
    FROM information_schema.columns
   WHERE table_schema = 'architecture_core'
     AND table_name = 'context_assertion_projection_receipt'
     AND column_name = 'context_profile_version';

  SELECT data_type
    INTO admission_version_type
    FROM information_schema.columns
   WHERE table_schema = 'architecture_core'
     AND table_name = 'context_assertion_projection_receipt'
     AND column_name = 'admission_version';

  IF profile_id_type IS DISTINCT FROM 'text'
     OR profile_version_type IS DISTINCT FROM 'integer'
     OR admission_version_type IS DISTINCT FROM 'integer' THEN
    RAISE EXCEPTION
      'Context Assertion receipt does not preserve exact CGC profile/admission identity';
  END IF;
END;
$$;
