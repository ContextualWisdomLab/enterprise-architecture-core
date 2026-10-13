BEGIN;

ALTER TABLE architecture_core.outbox_event
    ADD CONSTRAINT outbox_event_publish_chronology
    CHECK (
        published_at IS NULL
        OR published_at >= recorded_at
    );

ALTER TABLE architecture_core.projection_receipt
    ADD CONSTRAINT projection_receipt_process_chronology
    CHECK (
        processed_at IS NULL
        OR processed_at >= received_at
    );

COMMIT;
