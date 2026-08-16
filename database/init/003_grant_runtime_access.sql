\set ON_ERROR_STOP on

REVOKE ALL ON SCHEMA architecture_core FROM PUBLIC;
GRANT USAGE ON SCHEMA architecture_core TO ea_runtime;

REVOKE EXECUTE ON ALL FUNCTIONS IN SCHEMA architecture_core FROM PUBLIC;
GRANT EXECUTE ON FUNCTION architecture_core.current_tenant_id() TO ea_runtime;

GRANT SELECT
ON TABLE
    architecture_core.tenant_record,
    architecture_core.object_type,
    architecture_core.relation_type,
    architecture_core.lifecycle_phase
TO ea_runtime;

GRANT SELECT, INSERT, UPDATE
ON TABLE
    architecture_core.evidence_record,
    architecture_core.identity_link,
    architecture_core.architecture_object,
    architecture_core.object_revision,
    architecture_core.business_capability,
    architecture_core.organization_unit,
    architecture_core.application_record,
    architecture_core.application_interface,
    architecture_core.technology_provider,
    architecture_core.technology_component,
    architecture_core.technology_version,
    architecture_core.architecture_relation,
    architecture_core.lifecycle_interval,
    architecture_core.outbox_event,
    architecture_core.projection_receipt
TO ea_runtime;
