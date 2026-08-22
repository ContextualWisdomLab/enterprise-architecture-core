BEGIN;

CREATE FUNCTION architecture_core.validate_data_management_projection_authority()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  expected_tenant_code text;
  receipt_source_code text;
  receipt_status_code text;
  receipt_processed_at timestamptz;
BEGIN
  SELECT tenant_record.tenant_code
    INTO expected_tenant_code
    FROM architecture_core.tenant_record AS tenant_record
   WHERE tenant_record.tenant_record_id = NEW.tenant_record_id;

  IF expected_tenant_code IS NULL
     OR split_part(NEW.assessment_result_uri, ':', 3) IS DISTINCT FROM
        expected_tenant_code
     OR split_part(NEW.provenance_evidence_uri, ':', 3) IS DISTINCT FROM
        expected_tenant_code THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment result and provenance must remain inside the row tenant';
  END IF;

  SELECT
      split_part(receipt_record.event_source_uri, ':', 4),
      receipt_record.processing_status_code,
      receipt_record.processed_at
    INTO receipt_source_code, receipt_status_code, receipt_processed_at
    FROM architecture_core.projection_receipt AS receipt_record
   WHERE receipt_record.tenant_record_id = NEW.tenant_record_id
     AND receipt_record.projection_receipt_id = NEW.projection_receipt_id;

  IF receipt_source_code IS DISTINCT FROM 'semantic_data_portal'
     OR receipt_status_code IS DISTINCT FROM 'processed'
     OR receipt_processed_at IS NULL
     OR receipt_processed_at < NEW.source_recorded_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment projection requires processed semantic-data-portal receipt evidence';
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER data_management_assessment_projection_authority_guard
BEFORE INSERT
ON architecture_core.data_management_assessment_projection
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_data_management_projection_authority();

CREATE FUNCTION architecture_core.validate_assessment_improvement_source_truth()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  source_truth_status_code text;
  source_superseded_at timestamptz;
BEGIN
  SELECT
      projection_record.truth_status_code,
      projection_record.superseded_at
    INTO source_truth_status_code, source_superseded_at
    FROM architecture_core.data_management_assessment_projection AS projection_record
   WHERE projection_record.tenant_record_id = NEW.tenant_record_id
     AND projection_record.data_management_assessment_projection_id =
         NEW.data_management_assessment_projection_id;

  IF source_truth_status_code IS NULL
     OR source_truth_status_code IN ('rejected', 'superseded')
     OR source_superseded_at IS NOT NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'rejected or superseded assessment evidence cannot create improvement work';
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER assessment_improvement_plan_source_truth_guard
BEFORE INSERT
ON architecture_core.assessment_improvement_plan
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_assessment_improvement_source_truth();

COMMENT ON FUNCTION architecture_core.validate_data_management_projection_authority()
IS
'Fails closed when projected assessment identity or provenance crosses the tenant boundary, or when the source is not a processed semantic-data-portal receipt recorded after the assessment result.';

COMMENT ON FUNCTION architecture_core.validate_assessment_improvement_source_truth()
IS
'Prevents explicitly rejected, source-superseded, or system-superseded assessment evidence from creating new EA improvement work. Inferred or proposed source evidence may create proposed work only; it never becomes authoritative through projection.';

COMMIT;
