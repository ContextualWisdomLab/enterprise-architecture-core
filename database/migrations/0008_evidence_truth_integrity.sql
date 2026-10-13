BEGIN;

ALTER TABLE architecture_core.object_revision
    ADD CONSTRAINT object_revision_evidence_required
    CHECK (
        truth_status_code NOT IN ('authoritative', 'observed')
        OR evidence_record_id IS NOT NULL
    );

ALTER TABLE architecture_core.architecture_relation
    ADD CONSTRAINT architecture_relation_evidence_required
    CHECK (
        truth_status_code NOT IN ('authoritative', 'observed')
        OR evidence_record_id IS NOT NULL
    );

CREATE FUNCTION architecture_core.validate_evidence_record_tenant()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  expected_tenant_code text;
  evidence_tenant_code text;
BEGIN
  SELECT tenant_code
    INTO expected_tenant_code
    FROM architecture_core.tenant_record
   WHERE tenant_record_id = NEW.tenant_record_id;

  evidence_tenant_code := split_part(NEW.evidence_uri, ':', 3);
  IF expected_tenant_code IS NULL
     OR evidence_tenant_code IS DISTINCT FROM expected_tenant_code THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'evidence URI tenant does not match row tenant';
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER evidence_record_tenant_guard
BEFORE INSERT OR UPDATE OF tenant_record_id, evidence_uri
ON architecture_core.evidence_record
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_evidence_record_tenant();

COMMIT;
