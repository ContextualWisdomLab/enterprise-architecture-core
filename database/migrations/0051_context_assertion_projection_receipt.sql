BEGIN;

-- Context Assertion admission has identity that does not belong in the generic
-- projection_receipt row used by older projections. Keep the generic replay
-- receipt as the parent and attach only the versioned admission identity needed
-- to prove which released contract admitted the foreign evidence.
CREATE TABLE architecture_core.context_assertion_projection_receipt (
    tenant_record_id uuid NOT NULL,
    projection_receipt_id uuid NOT NULL,
    event_specversion text NOT NULL,
    event_type text NOT NULL,
    event_subject_uri text NOT NULL,
    event_time timestamptz NOT NULL,
    event_dataschema_uri text NOT NULL,
    transport_media_type text NOT NULL,
    context_profile_version text NOT NULL,
    admission_version text NOT NULL,
    provenance_evidence_record_id uuid NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT context_assertion_projection_receipt_primary_key
        PRIMARY KEY (tenant_record_id, projection_receipt_id),
    CONSTRAINT context_assertion_projection_receipt_parent_foreign
        FOREIGN KEY (tenant_record_id, projection_receipt_id)
        REFERENCES architecture_core.projection_receipt
            (tenant_record_id, projection_receipt_id),
    CONSTRAINT context_assertion_projection_receipt_provenance_foreign
        FOREIGN KEY (tenant_record_id, provenance_evidence_record_id)
        REFERENCES architecture_core.evidence_record
            (tenant_record_id, evidence_record_id),
    CONSTRAINT context_assertion_projection_receipt_specversion
        CHECK (event_specversion = '1.0'),
    CONSTRAINT context_assertion_projection_receipt_type
        CHECK (
            event_type =
            'org.contextualwisdomlab.context_graph.assertion.v1'
        ),
    CONSTRAINT context_assertion_projection_receipt_subject_uri_format
        CHECK (
            length(event_subject_uri) BETWEEN 1 AND 2048
            AND event_subject_uri ~
            '^urn:cwl:(?=[^:]{2,63}:)[a-z][a-z0-9]+(?:_[a-z0-9]+)*:(?=[^:]{2,63}:)[a-z][a-z0-9]+(?:_[a-z0-9]+)*:(?=[^:]{2,63}:)[a-z][a-z0-9]+(?:_[a-z0-9]+)*:[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$'
        ),
    CONSTRAINT context_assertion_projection_receipt_dataschema
        CHECK (
            event_dataschema_uri =
            'https://schemas.contextualwisdomlab.org/context/context-assertion.v1.schema.json'
        ),
    CONSTRAINT context_assertion_projection_receipt_media_type
        CHECK (transport_media_type = 'application/cloudevents+json'),
    CONSTRAINT context_assertion_projection_receipt_profile_version
        CHECK (
            length(context_profile_version) BETWEEN 1 AND 128
            AND context_profile_version ~ '^[a-z0-9][a-z0-9._/-]*$'
        ),
    CONSTRAINT context_assertion_projection_receipt_admission_version
        CHECK (
            length(admission_version) BETWEEN 1 AND 128
            AND admission_version ~ '^[a-z0-9][a-z0-9._/-]*$'
        )
);

CREATE FUNCTION architecture_core.validate_context_assertion_receipt_tenant()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  expected_tenant_code text;
BEGIN
  SELECT tenant_code
    INTO expected_tenant_code
    FROM architecture_core.tenant_record
   WHERE tenant_record_id = NEW.tenant_record_id;

  IF expected_tenant_code IS NULL
     OR split_part(NEW.event_subject_uri, ':', 3)
        IS DISTINCT FROM expected_tenant_code THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'Context Assertion subject tenant does not match receipt tenant';
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER context_assertion_projection_receipt_tenant_guard
BEFORE INSERT OR UPDATE OF tenant_record_id, event_subject_uri
ON architecture_core.context_assertion_projection_receipt
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_context_assertion_receipt_tenant();

CREATE FUNCTION architecture_core.reject_context_assertion_receipt_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION USING
    ERRCODE = '23514',
    MESSAGE = 'Context Assertion projection receipt identity is immutable';
END;
$$;

CREATE TRIGGER context_assertion_projection_receipt_history_guard
BEFORE UPDATE OR DELETE
ON architecture_core.context_assertion_projection_receipt
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_context_assertion_receipt_mutation();

ALTER TABLE architecture_core.context_assertion_projection_receipt
    ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.context_assertion_projection_receipt
    FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy
ON architecture_core.context_assertion_projection_receipt
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

CREATE INDEX context_assertion_projection_receipt_provenance_index
    ON architecture_core.context_assertion_projection_receipt
        (tenant_record_id, provenance_evidence_record_id, recorded_at DESC);

COMMENT ON TABLE architecture_core.context_assertion_projection_receipt IS
'Retains immutable Context Assertion CloudEvent and admission identity beside the generic replay receipt. The row preserves source-event compatibility/provenance evidence without transferring upstream product authority or copying the foreign product model.';

COMMIT;
