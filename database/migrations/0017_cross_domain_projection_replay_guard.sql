BEGIN;

ALTER TABLE architecture_core.application_context_projection
    ADD CONSTRAINT application_context_projection_receipt_fact_unique
    UNIQUE (
        tenant_record_id,
        projection_receipt_id,
        application_object_id,
        external_context_reference_id,
        projection_relation_code
    );

COMMIT;
