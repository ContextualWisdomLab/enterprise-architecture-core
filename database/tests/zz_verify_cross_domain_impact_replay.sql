\set ON_ERROR_STOP on

-- A processed foreign event may be delivered repeatedly. Replaying the same
-- receipt-bound fact must not create a second active projection row.

SET ROLE ea_runtime;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.application_context_projection (
        tenant_record_id,
        application_context_projection_id,
        application_object_id,
        external_context_reference_id,
        projection_receipt_id,
        projection_relation_code,
        truth_status_code,
        valid_from,
        recorded_at
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f200-4000-7400-8400-000000000099',
        '0195d145-64e8-7f4f-8a23-a0cc784cb902',
        '0196f200-2000-7200-8200-000000000003',
        '0196f200-1000-7100-8100-000000000003',
        'impacts',
        'inferred',
        '2026-08-21T00:00:00Z',
        '2026-08-21T00:03:00Z'
    );
    RAISE EXCEPTION 'replayed external impact fact created a duplicate row';
  EXCEPTION
    WHEN unique_violation THEN NULL;
  END;
END;
$$;

RESET ROLE;
