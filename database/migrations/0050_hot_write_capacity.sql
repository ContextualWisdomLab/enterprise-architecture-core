BEGIN;

CREATE FUNCTION architecture_core.hot_partition_bucket(
    requested_tenant_record_id uuid
)
RETURNS smallint
LANGUAGE sql
IMMUTABLE
PARALLEL SAFE
AS $$
    SELECT (
        (
            hashtextextended(requested_tenant_record_id::text, 0)
            & 9223372036854775807
        ) % 16
    )::smallint;
$$;

COMMENT ON FUNCTION architecture_core.hot_partition_bucket(uuid) IS
    'Stable tenant-derived 0..15 routing key for a future hot-write partition cutover.';

ALTER TABLE architecture_core.evidence_record SET (fillfactor = 80);
ALTER TABLE architecture_core.outbox_event SET (fillfactor = 80);
ALTER TABLE architecture_core.projection_receipt SET (fillfactor = 80);
ALTER TABLE architecture_core.transformation_history_record
    SET (fillfactor = 80);

CREATE INDEX evidence_record_hot_write_index
    ON architecture_core.evidence_record
        (
            tenant_record_id,
            (architecture_core.hot_partition_bucket(tenant_record_id)),
            recorded_at,
            evidence_record_id
        );

CREATE INDEX outbox_event_hot_write_index
    ON architecture_core.outbox_event
        (
            tenant_record_id,
            (architecture_core.hot_partition_bucket(tenant_record_id)),
            recorded_at,
            outbox_event_id
        )
    WHERE publish_status_code IN ('pending', 'failed');

CREATE INDEX projection_receipt_hot_write_index
    ON architecture_core.projection_receipt
        (
            tenant_record_id,
            (architecture_core.hot_partition_bucket(tenant_record_id)),
            processing_status_code,
            received_at,
            projection_receipt_id
        );

CREATE INDEX transformation_history_hot_write_index
    ON architecture_core.transformation_history_record
        (
            tenant_record_id,
            (architecture_core.hot_partition_bucket(tenant_record_id)),
            recorded_at,
            transformation_history_record_id
        );

COMMENT ON TABLE architecture_core.evidence_record IS
    'Append-only evidence boundary; tenant-first routing and fillfactor prepare a future hash/list partition cutover.';
COMMENT ON TABLE architecture_core.outbox_event IS
    'Append-only publication boundary; pending work is tenant-routed for future hot-write partitioning.';
COMMENT ON TABLE architecture_core.projection_receipt IS
    'Append-only inbound-receipt boundary; tenant-routed status scans prepare future hot-write partitioning.';
COMMENT ON TABLE architecture_core.transformation_history_record IS
    'Append-only transformation history boundary; tenant-routed writes prepare future hot-write partitioning.';

COMMIT;
