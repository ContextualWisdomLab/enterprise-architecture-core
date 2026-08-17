\set ON_ERROR_STOP on

-- A source string that preserves the tenant and product at colon positions 3/4
-- must still be rejected unless it is the exact Context Graph canonical
-- authority URI shape. Otherwise an attacker could satisfy legacy split_part
-- guards with a forged prefix or appended path.
--
-- Canonical syntax alone is not enough: the tenant embedded in a source URI
-- must equal the tenant that owns the receipt row. Otherwise a valid-looking
-- foreign-tenant authority can be replayed into another tenant's evidence
-- history while still passing RLS on the local row.

SET ROLE ea_runtime;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.projection_receipt (
        tenant_record_id,
        projection_receipt_id,
        event_source_uri,
        event_identifier,
        payload_sha256,
        schema_version,
        received_at,
        processed_at,
        processing_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f201-1000-7100-8100-000000000001',
        'evil:cwl:tenant_001:pg_erd_cloud:forged',
        '0196f201-1000-7100-8100-000000000101',
        repeat('a', 64),
        'context-assertion/v1',
        '2026-08-23T00:00:00Z',
        '2026-08-23T00:01:00Z',
        'processed'
    );
    RAISE EXCEPTION 'non-canonical projection source URI was accepted';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.projection_receipt (
        tenant_record_id,
        projection_receipt_id,
        event_source_uri,
        event_identifier,
        payload_sha256,
        schema_version,
        received_at,
        processed_at,
        processing_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196f201-1000-7100-8100-000000000002',
        'urn:cwl:tenant_999:pg_erd_cloud',
        '0196f201-1000-7100-8100-000000000102',
        repeat('b', 64),
        'context-assertion/v1',
        '2026-08-23T00:02:00Z',
        '2026-08-23T00:03:00Z',
        'processed'
    );
    RAISE EXCEPTION 'foreign-tenant projection source URI was accepted';
  EXCEPTION
    WHEN check_violation THEN NULL;
  END;
END;
$$;

RESET ROLE;
