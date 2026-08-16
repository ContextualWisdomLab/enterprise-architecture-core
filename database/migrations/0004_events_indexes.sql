BEGIN;

CREATE TABLE architecture_core.outbox_event (
    tenant_record_id uuid NOT NULL,
    outbox_event_id uuid NOT NULL DEFAULT uuidv7(),
    aggregate_object_id uuid NOT NULL,
    event_type_code text NOT NULL,
    event_payload_json jsonb NOT NULL,
    event_schema_version text NOT NULL,
    correlation_event_id uuid,
    causation_event_id uuid,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    published_at timestamptz,
    publish_attempt_count integer NOT NULL DEFAULT 0,
    publish_status_code text NOT NULL DEFAULT 'pending',
    CONSTRAINT outbox_event_primary_key
        PRIMARY KEY (tenant_record_id, outbox_event_id),
    CONSTRAINT outbox_event_tenant_foreign
        FOREIGN KEY (tenant_record_id)
        REFERENCES architecture_core.tenant_record (tenant_record_id),
    CONSTRAINT outbox_event_object_foreign
        FOREIGN KEY (tenant_record_id, aggregate_object_id)
        REFERENCES architecture_core.architecture_object
            (tenant_record_id, architecture_object_id),
    CONSTRAINT outbox_event_type_format
        CHECK (
            event_type_code ~
            '^org\.contextualwisdomlab\.ea\.[a-z0-9_.]+\.v[1-9][0-9]*$'
        ),
    CONSTRAINT outbox_event_attempt_nonnegative
        CHECK (publish_attempt_count >= 0),
    CONSTRAINT outbox_event_status_allowed
        CHECK (
            publish_status_code IN (
                'pending',
                'publishing',
                'published',
                'failed'
            )
        )
);

CREATE TABLE architecture_core.projection_receipt (
    tenant_record_id uuid NOT NULL,
    projection_receipt_id uuid NOT NULL DEFAULT uuidv7(),
    event_source_uri text NOT NULL,
    event_identifier text NOT NULL,
    payload_sha256 text NOT NULL,
    schema_version text NOT NULL,
    received_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    processed_at timestamptz,
    processing_status_code text NOT NULL DEFAULT 'received',
    failure_code text,
    CONSTRAINT projection_receipt_primary_key
        PRIMARY KEY (tenant_record_id, projection_receipt_id),
    CONSTRAINT projection_receipt_tenant_foreign
        FOREIGN KEY (tenant_record_id)
        REFERENCES architecture_core.tenant_record (tenant_record_id),
    CONSTRAINT projection_receipt_identity_unique
        UNIQUE (tenant_record_id, event_source_uri, event_identifier),
    CONSTRAINT projection_receipt_digest_format
        CHECK (payload_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT projection_receipt_status_allowed
        CHECK (
            processing_status_code IN (
                'received',
                'processing',
                'processed',
                'failed',
                'rejected'
            )
        )
);

ALTER TABLE architecture_core.outbox_event ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.outbox_event FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.outbox_event
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.projection_receipt ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.projection_receipt FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.projection_receipt
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

CREATE INDEX architecture_object_tenant_index
    ON architecture_core.architecture_object
        (tenant_record_id, object_type_id);
CREATE INDEX object_revision_current_index
    ON architecture_core.object_revision
        (tenant_record_id, architecture_object_id, valid_from DESC)
    WHERE superseded_at IS NULL;
CREATE INDEX architecture_relation_source_index
    ON architecture_core.architecture_relation
        (tenant_record_id, source_object_id, relation_type_id)
    WHERE superseded_at IS NULL;
CREATE INDEX architecture_relation_target_index
    ON architecture_core.architecture_relation
        (tenant_record_id, target_object_id, relation_type_id)
    WHERE superseded_at IS NULL;
CREATE INDEX lifecycle_interval_object_index
    ON architecture_core.lifecycle_interval
        (tenant_record_id, architecture_object_id, valid_from DESC)
    WHERE superseded_at IS NULL;
CREATE INDEX outbox_event_pending_index
    ON architecture_core.outbox_event
        (tenant_record_id, recorded_at, outbox_event_id)
    WHERE publish_status_code IN ('pending', 'failed');
CREATE INDEX projection_receipt_status_index
    ON architecture_core.projection_receipt
        (tenant_record_id, processing_status_code, received_at);

COMMIT;
