BEGIN;

CREATE TABLE architecture_core.business_capability (
    tenant_record_id uuid NOT NULL,
    architecture_object_id uuid NOT NULL,
    capability_code text NOT NULL,
    capability_level integer NOT NULL,
    CONSTRAINT business_capability_primary_key
        PRIMARY KEY (tenant_record_id, architecture_object_id),
    CONSTRAINT business_capability_object_foreign
        FOREIGN KEY (tenant_record_id, architecture_object_id)
        REFERENCES architecture_core.architecture_object
            (tenant_record_id, architecture_object_id),
    CONSTRAINT business_capability_code_nonempty
        CHECK (length(btrim(capability_code)) > 0),
    CONSTRAINT business_capability_level_positive
        CHECK (capability_level > 0),
    CONSTRAINT business_capability_code_unique
        UNIQUE (tenant_record_id, capability_code)
);

CREATE TABLE architecture_core.organization_unit (
    tenant_record_id uuid NOT NULL,
    architecture_object_id uuid NOT NULL,
    organization_code text NOT NULL,
    organization_kind_code text NOT NULL,
    CONSTRAINT organization_unit_primary_key
        PRIMARY KEY (tenant_record_id, architecture_object_id),
    CONSTRAINT organization_unit_object_foreign
        FOREIGN KEY (tenant_record_id, architecture_object_id)
        REFERENCES architecture_core.architecture_object
            (tenant_record_id, architecture_object_id),
    CONSTRAINT organization_unit_code_nonempty
        CHECK (length(btrim(organization_code)) > 0),
    CONSTRAINT organization_unit_kind_format
        CHECK (organization_kind_code ~ '^[a-z][a-z0-9_]+$'),
    CONSTRAINT organization_unit_code_unique
        UNIQUE (tenant_record_id, organization_code)
);

CREATE TABLE architecture_core.application_record (
    tenant_record_id uuid NOT NULL,
    architecture_object_id uuid NOT NULL,
    application_code text NOT NULL,
    application_category_code text NOT NULL,
    CONSTRAINT application_record_primary_key
        PRIMARY KEY (tenant_record_id, architecture_object_id),
    CONSTRAINT application_record_object_foreign
        FOREIGN KEY (tenant_record_id, architecture_object_id)
        REFERENCES architecture_core.architecture_object
            (tenant_record_id, architecture_object_id),
    CONSTRAINT application_record_code_nonempty
        CHECK (length(btrim(application_code)) > 0),
    CONSTRAINT application_record_category_format
        CHECK (application_category_code ~ '^[a-z][a-z0-9_]+$'),
    CONSTRAINT application_record_code_unique
        UNIQUE (tenant_record_id, application_code)
);

CREATE TABLE architecture_core.application_interface (
    tenant_record_id uuid NOT NULL,
    architecture_object_id uuid NOT NULL,
    interface_protocol_code text NOT NULL,
    interface_direction_code text NOT NULL,
    interface_exposure_code text NOT NULL DEFAULT 'internal',
    CONSTRAINT application_interface_primary_key
        PRIMARY KEY (tenant_record_id, architecture_object_id),
    CONSTRAINT application_interface_object_foreign
        FOREIGN KEY (tenant_record_id, architecture_object_id)
        REFERENCES architecture_core.architecture_object
            (tenant_record_id, architecture_object_id),
    CONSTRAINT application_interface_protocol_format
        CHECK (interface_protocol_code ~ '^[a-z][a-z0-9_]+$'),
    CONSTRAINT application_interface_direction_allowed
        CHECK (
            interface_direction_code IN (
                'inbound',
                'outbound',
                'bidirectional'
            )
        ),
    CONSTRAINT application_interface_exposure_format
        CHECK (interface_exposure_code ~ '^[a-z][a-z0-9_]+$')
);

CREATE TABLE architecture_core.technology_provider (
    tenant_record_id uuid NOT NULL,
    architecture_object_id uuid NOT NULL,
    provider_code text NOT NULL,
    provider_website_uri text,
    CONSTRAINT technology_provider_primary_key
        PRIMARY KEY (tenant_record_id, architecture_object_id),
    CONSTRAINT technology_provider_object_foreign
        FOREIGN KEY (tenant_record_id, architecture_object_id)
        REFERENCES architecture_core.architecture_object
            (tenant_record_id, architecture_object_id),
    CONSTRAINT technology_provider_code_nonempty
        CHECK (length(btrim(provider_code)) > 0),
    CONSTRAINT technology_provider_code_unique
        UNIQUE (tenant_record_id, provider_code)
);

CREATE TABLE architecture_core.technology_component (
    tenant_record_id uuid NOT NULL,
    architecture_object_id uuid NOT NULL,
    component_code text NOT NULL,
    component_category_code text NOT NULL,
    CONSTRAINT technology_component_primary_key
        PRIMARY KEY (tenant_record_id, architecture_object_id),
    CONSTRAINT technology_component_object_foreign
        FOREIGN KEY (tenant_record_id, architecture_object_id)
        REFERENCES architecture_core.architecture_object
            (tenant_record_id, architecture_object_id),
    CONSTRAINT technology_component_code_nonempty
        CHECK (length(btrim(component_code)) > 0),
    CONSTRAINT technology_component_category_format
        CHECK (component_category_code ~ '^[a-z][a-z0-9_]+$'),
    CONSTRAINT technology_component_code_unique
        UNIQUE (tenant_record_id, component_code)
);

CREATE TABLE architecture_core.technology_version (
    tenant_record_id uuid NOT NULL,
    architecture_object_id uuid NOT NULL,
    version_label text NOT NULL,
    release_date date,
    support_end_date date,
    CONSTRAINT technology_version_primary_key
        PRIMARY KEY (tenant_record_id, architecture_object_id),
    CONSTRAINT technology_version_object_foreign
        FOREIGN KEY (tenant_record_id, architecture_object_id)
        REFERENCES architecture_core.architecture_object
            (tenant_record_id, architecture_object_id),
    CONSTRAINT technology_version_label_nonempty
        CHECK (length(btrim(version_label)) > 0),
    CONSTRAINT technology_version_support_order
        CHECK (
            support_end_date IS NULL
            OR release_date IS NULL
            OR support_end_date >= release_date
        )
);

ALTER TABLE architecture_core.business_capability ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.business_capability FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.business_capability
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.organization_unit ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.organization_unit FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.organization_unit
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.application_record ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.application_record FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.application_record
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.application_interface ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.application_interface FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.application_interface
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.technology_provider ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.technology_provider FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.technology_provider
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.technology_component ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.technology_component FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.technology_component
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.technology_version ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.technology_version FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.technology_version
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

COMMIT;
