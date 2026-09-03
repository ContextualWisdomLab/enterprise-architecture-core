\set ON_ERROR_STOP on

-- Final executable cross-boundary invariant: the same milestone completion
-- produced by the evidence-closure command must expose its outbox causal link
-- inside the privacy-minimized event data advertised by AsyncAPI.

RESET ROLE;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
DECLARE
  milestone_event_count integer;
  misaligned_event_count integer;
BEGIN
  SELECT count(*)
    INTO milestone_event_count
    FROM architecture_core.outbox_event AS event_record
   WHERE event_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND event_record.event_type_code =
         'org.contextualwisdomlab.ea.data_management.milestone_completed.v1';

  IF milestone_event_count < 1 THEN
    RAISE EXCEPTION
      'data-management acceptance suite produced no milestone completion event';
  END IF;

  SELECT count(*)
    INTO misaligned_event_count
    FROM architecture_core.outbox_event AS event_record
   WHERE event_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND event_record.event_type_code =
         'org.contextualwisdomlab.ea.data_management.milestone_completed.v1'
     AND (
       event_record.causation_event_id IS NULL
       OR event_record.event_payload_json ->> 'causation_event_id'
          IS DISTINCT FROM event_record.causation_event_id::text
     );

  IF misaligned_event_count <> 0 THEN
    RAISE EXCEPTION
      'milestone completion event data lost its transactional causal link: %',
      misaligned_event_count;
  END IF;
END;
$$;
