BEGIN;

CREATE TABLE architecture_core.relation_type (
    relation_type_id uuid PRIMARY KEY DEFAULT uuidv7(),
    relation_type_code text NOT NULL,
    source_type_id uuid,
    target_type_id uuid,
    forward_only_flag boolean NOT NULL DEFAULT false,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT relation_type_code_unique UNIQUE (relation_type_code),
    CONSTRAINT relation_type_source_foreign
        FOREIGN KEY (source_type_id)
        REFERENCES architecture_core.object_type (object_type_id),
    CONSTRAINT relation_type_target_foreign
        FOREIGN KEY (target_type_id)
        REFERENCES architecture_core.object_type (object_type_id),
    CONSTRAINT relation_type_code_format
        CHECK (relation_type_code ~ '^[a-z][a-z0-9_]+$')
);

CREATE TABLE architecture_core.architecture_relation (
    tenant_record_id uuid NOT NULL,
    architecture_relation_id uuid NOT NULL DEFAULT uuidv7(),
    relation_type_id uuid NOT NULL,
    source_object_id uuid NOT NULL,
    target_object_id uuid NOT NULL,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    superseded_at timestamptz,
    truth_status_code text NOT NULL,
    evidence_record_id uuid,
    CONSTRAINT architecture_relation_primary_key
        PRIMARY KEY (tenant_record_id, architecture_relation_id),
    CONSTRAINT architecture_relation_tenant_foreign
        FOREIGN KEY (tenant_record_id)
        REFERENCES architecture_core.tenant_record (tenant_record_id),
    CONSTRAINT architecture_relation_type_foreign
        FOREIGN KEY (relation_type_id)
        REFERENCES architecture_core.relation_type (relation_type_id),
    CONSTRAINT architecture_relation_source_foreign
        FOREIGN KEY (tenant_record_id, source_object_id)
        REFERENCES architecture_core.architecture_object
            (tenant_record_id, architecture_object_id),
    CONSTRAINT architecture_relation_target_foreign
        FOREIGN KEY (tenant_record_id, target_object_id)
        REFERENCES architecture_core.architecture_object
            (tenant_record_id, architecture_object_id),
    CONSTRAINT architecture_relation_evidence_foreign
        FOREIGN KEY (tenant_record_id, evidence_record_id)
        REFERENCES architecture_core.evidence_record
            (tenant_record_id, evidence_record_id),
    CONSTRAINT architecture_relation_no_self
        CHECK (source_object_id <> target_object_id),
    CONSTRAINT architecture_relation_valid_interval
        CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT architecture_relation_system_interval
        CHECK (superseded_at IS NULL OR superseded_at >= recorded_at),
    CONSTRAINT architecture_relation_truth_allowed
        CHECK (
            truth_status_code IN (
                'authoritative',
                'observed',
                'inferred',
                'proposed',
                'superseded',
                'rejected'
            )
        )
);

CREATE TABLE architecture_core.lifecycle_phase (
    lifecycle_phase_id uuid PRIMARY KEY DEFAULT uuidv7(),
    lifecycle_phase_code text NOT NULL,
    display_order integer NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT lifecycle_phase_code_unique UNIQUE (lifecycle_phase_code),
    CONSTRAINT lifecycle_phase_code_format
        CHECK (lifecycle_phase_code ~ '^[a-z][a-z0-9_]+$'),
    CONSTRAINT lifecycle_phase_order_positive CHECK (display_order > 0)
);

CREATE TABLE architecture_core.lifecycle_interval (
    tenant_record_id uuid NOT NULL,
    lifecycle_interval_id uuid NOT NULL DEFAULT uuidv7(),
    architecture_object_id uuid NOT NULL,
    lifecycle_phase_id uuid NOT NULL,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    superseded_at timestamptz,
    evidence_record_id uuid,
    CONSTRAINT lifecycle_interval_primary_key
        PRIMARY KEY (tenant_record_id, lifecycle_interval_id),
    CONSTRAINT lifecycle_interval_object_foreign
        FOREIGN KEY (tenant_record_id, architecture_object_id)
        REFERENCES architecture_core.architecture_object
            (tenant_record_id, architecture_object_id),
    CONSTRAINT lifecycle_interval_phase_foreign
        FOREIGN KEY (lifecycle_phase_id)
        REFERENCES architecture_core.lifecycle_phase (lifecycle_phase_id),
    CONSTRAINT lifecycle_interval_evidence_foreign
        FOREIGN KEY (tenant_record_id, evidence_record_id)
        REFERENCES architecture_core.evidence_record
            (tenant_record_id, evidence_record_id),
    CONSTRAINT lifecycle_interval_valid_order
        CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT lifecycle_interval_system_order
        CHECK (superseded_at IS NULL OR superseded_at >= recorded_at)
);

ALTER TABLE architecture_core.architecture_relation ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.architecture_relation FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.architecture_relation
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.lifecycle_interval ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.lifecycle_interval FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.lifecycle_interval
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

COMMIT;
