\set ON_ERROR_STOP on

-- Historical impact queries rely on the processed receipt remaining the same
-- fact after it has become terminal. A later status or digest rewrite must not
-- erase or substitute evidence that was visible at an earlier system cutoff.

SET ROLE ea_runtime;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.projection_receipt
       SET processing_status_code = 'rejected',
           failure_code = 'late_reclassification'
     WHERE tenant_record_id =
           '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND projection_receipt_id =
           '0196f200-1000-7100-8100-000000000001';
    RAISE EXCEPTION 'processed projection receipt status was rewritten';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.projection_receipt
       SET payload_sha256 = repeat('b', 64)
     WHERE tenant_record_id =
           '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND projection_receipt_id =
           '0196f200-1000-7100-8100-000000000001';
    RAISE EXCEPTION 'processed projection receipt payload digest was rewritten';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    DELETE FROM architecture_core.projection_receipt
     WHERE tenant_record_id =
           '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND projection_receipt_id =
           '0196f200-1000-7100-8100-000000000001';
    RAISE EXCEPTION 'processed projection receipt history was hard-deleted';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

RESET ROLE;
