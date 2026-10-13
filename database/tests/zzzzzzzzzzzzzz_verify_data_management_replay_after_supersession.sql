\set ON_ERROR_STOP on

-- An exact retry of a previously committed improvement decision must remain
-- idempotent after a newer assessment supersedes its source projection. This
-- models a caller retrying after losing the original receipt while the source
-- system has already published a replacement assessment.

RESET ROLE;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
DECLARE
  original_projection_id uuid;
  original_plan_id uuid;
  original_event_id uuid;
  replay_plan_id uuid;
  replay_event_id uuid;
BEGIN
  SELECT projection.data_management_assessment_projection_id
    INTO original_projection_id
    FROM architecture_core.data_management_assessment_projection AS projection
   WHERE projection.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND projection.assessment_result_uri =
         'urn:cwl:tenant_001:data_context:data_management_assessment:0196f101-1111-7111-8111-111111111111'
     AND projection.superseded_at IS NOT NULL;

  SELECT plan_record.assessment_improvement_plan_id
    INTO original_plan_id
    FROM architecture_core.assessment_improvement_plan AS plan_record
   WHERE plan_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND plan_record.decision_request_id =
         '0196f103-1111-7111-8111-111111111111';

  SELECT event_record.outbox_event_id
    INTO original_event_id
    FROM architecture_core.outbox_event AS event_record
   WHERE event_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND event_record.decision_request_id =
         '0196f103-1111-7111-8111-111111111111'
     AND event_record.event_type_code =
         'org.contextualwisdomlab.ea.data_management.improvement_initiative_created.v1';

  IF original_projection_id IS NULL
     OR original_plan_id IS NULL
     OR original_event_id IS NULL THEN
    RAISE EXCEPTION 'superseded decision fixture is incomplete';
  END IF;

  SELECT
      result.assessment_improvement_plan_id,
      result.outbox_event_id
    INTO replay_plan_id, replay_event_id
    FROM architecture_core.create_data_management_improvement_plan(
      original_projection_id,
      'control_evidence',
      '0196f103-1111-7111-8111-111111111111',
      '0195d145-64e8-7f4f-8a23-a0cc784cb901',
      '0196f100-1111-7111-8111-111111111110',
      'close_control_evidence_gap',
      'Close control evidence gap',
      'control_evidence_accepted',
      'Control evidence accepted',
      '2026-11-30T00:00:00Z',
      'portfolio://fy2026/data-governance'
    ) AS result;

  IF replay_plan_id IS DISTINCT FROM original_plan_id
     OR replay_event_id IS DISTINCT FROM original_event_id THEN
    RAISE EXCEPTION
      'superseded-source replay changed committed decision receipt: %, %',
      replay_plan_id,
      replay_event_id;
  END IF;
END;
$$;
