BEGIN;

CREATE SCHEMA IF NOT EXISTS architecture_core;

CREATE FUNCTION architecture_core.current_tenant_id()
RETURNS uuid
LANGUAGE sql
STABLE
PARALLEL SAFE
AS $$
    SELECT NULLIF(current_setting('app.tenant_record_id', true), '')::uuid;
$$;

CREATE TABLE architecture_core.tenant_record (
    tenant_record_id uuid PRIMARY KEY DEFAULT uuidv7(),
    tenant_code text NOT NULL,
    tenant_title text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT tenant_record_code_unique UNIQUE (tenant_code),
    CONSTRAINT tenant_record_code_nonempty CHECK (length(btrim(tenant_code)) > 0),
    CONSTRAINT tenant_record_title_nonempty CHECK (length(btrim(tenant_title)) > 0)
);

CREATE TABLE architecture_core.evidence_record (
    tenant_record_id uuid NOT NULL,
    evidence_record_id uuid NOT NULL DEFAULT uuidv7(),
    evidence_uri text NOT NULL,
    sha256_digest text NOT NULL,
    source_locator text,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT evidence_record_primary_key
        PRIMARY KEY (tenant_record_id, evidence_record_id),
    CONSTRAINT evidence_record_tenant_foreign
        FOREIGN KEY (tenant_record_id)
        REFERENCES architecture_core.tenant_record (tenant_record_id),
    CONSTRAINT evidence_record_digest_format
        CHECK (sha256_digest ~ '^[0-9a-f]{64}$'),
    CONSTRAINT evidence_record_uri_nonempty
        CHECK (length(btrim(evidence_uri)) > 0),
    CONSTRAINT evidence_record_identity_unique
        UNIQUE (tenant_record_id, evidence_uri, sha256_digest)
);

CREATE TABLE architecture_core.identity_link (
    tenant_record_id uuid NOT NULL,
    identity_link_id uuid NOT NULL DEFAULT uuidv7(),
    keyverse_subject_id text NOT NULL,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    superseded_at timestamptz,
    CONSTRAINT identity_link_primary_key
        PRIMARY KEY (tenant_record_id, identity_link_id),
    CONSTRAINT identity_link_tenant_foreign
        FOREIGN KEY (tenant_record_id)
        REFERENCES architecture_core.tenant_record (tenant_record_id),
    CONSTRAINT identity_link_valid_interval
        CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT identity_link_system_interval
        CHECK (superseded_at IS NULL OR superseded_at >= recorded_at),
    CONSTRAINT identity_link_subject_unique
        UNIQUE (tenant_record_id, keyverse_subject_id, valid_from)
);

CREATE TABLE architecture_core.object_type (
    object_type_id uuid PRIMARY KEY DEFAULT uuidv7(),
    object_type_code text NOT NULL,
    object_type_title text NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT object_type_code_unique UNIQUE (object_type_code),
    CONSTRAINT object_type_code_format
        CHECK (object_type_code ~ '^[a-z][a-z0-9_]+$'),
    CONSTRAINT object_type_title_nonempty
        CHECK (length(btrim(object_type_title)) > 0)
);

CREATE TABLE architecture_core.architecture_object (
    tenant_record_id uuid NOT NULL,
    architecture_object_id uuid NOT NULL DEFAULT uuidv7(),
    object_type_id uuid NOT NULL,
    canonical_asset_uri text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT architecture_object_primary_key
        PRIMARY KEY (tenant_record_id, architecture_object_id),
    CONSTRAINT architecture_object_tenant_foreign
        FOREIGN KEY (tenant_record_id)
        REFERENCES architecture_core.tenant_record (tenant_record_id),
    CONSTRAINT architecture_object_type_foreign
        FOREIGN KEY (object_type_id)
        REFERENCES architecture_core.object_type (object_type_id),
    CONSTRAINT architecture_object_uri_unique
        UNIQUE (tenant_record_id, canonical_asset_uri),
    CONSTRAINT architecture_object_uri_format
        CHECK (
            canonical_asset_uri ~
            '^urn:cwl:[a-z][a-z0-9_]{1,62}:ea_core:[a-z][a-z0-9_]{1,62}:[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        )
);

CREATE TABLE architecture_core.object_revision (
    tenant_record_id uuid NOT NULL,
    object_revision_id uuid NOT NULL DEFAULT uuidv7(),
    architecture_object_id uuid NOT NULL,
    revision_number integer NOT NULL,
    object_title text NOT NULL,
    object_description text,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    superseded_at timestamptz,
    truth_status_code text NOT NULL,
    evidence_record_id uuid,
    CONSTRAINT object_revision_primary_key
        PRIMARY KEY (tenant_record_id, object_revision_id),
    CONSTRAINT object_revision_object_foreign
        FOREIGN KEY (tenant_record_id, architecture_object_id)
        REFERENCES architecture_core.architecture_object
            (tenant_record_id, architecture_object_id),
    CONSTRAINT object_revision_evidence_foreign
        FOREIGN KEY (tenant_record_id, evidence_record_id)
        REFERENCES architecture_core.evidence_record
            (tenant_record_id, evidence_record_id),
    CONSTRAINT object_revision_number_positive CHECK (revision_number > 0),
    CONSTRAINT object_revision_title_nonempty
        CHECK (length(btrim(object_title)) > 0),
    CONSTRAINT object_revision_valid_interval
        CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT object_revision_system_interval
        CHECK (superseded_at IS NULL OR superseded_at >= recorded_at),
    CONSTRAINT object_revision_truth_allowed
        CHECK (
            truth_status_code IN (
                'authoritative',
                'observed',
                'inferred',
                'proposed',
                'superseded',
                'rejected'
            )
        ),
    CONSTRAINT object_revision_sequence_unique
        UNIQUE (tenant_record_id, architecture_object_id, revision_number)
);

ALTER TABLE architecture_core.tenant_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.tenant_record FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.tenant_record
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.evidence_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.evidence_record FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.evidence_record
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.identity_link ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.identity_link FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.identity_link
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.architecture_object ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.architecture_object FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.architecture_object
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.object_revision ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.object_revision FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.object_revision
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

COMMIT;
