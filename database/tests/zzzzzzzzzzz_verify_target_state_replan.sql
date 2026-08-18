\set ON_ERROR_STOP on

-- Buyer acceptance for replacing a terminal gap-detected target state.
-- Replanning must preserve the predecessor's immutable history, create a distinct
-- governed replacement, and commit history/replan/outbox evidence atomically.

DO $$
BEGIN
  IF to_regprocedure(
      'architecture_core.record_target_state_replan(uuid,uuid,uuid,uuid,uuid,uuid,text,text,text,timestamptz,text,text,uuid)'
     ) IS NULL THEN
    RAISE EXCEPTION 'purpose-bound target-state replan command is missing';
  END IF;
END;
$$;

SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

-- Monitoring has already established fresh verified evidence. Model a later
-- human verification that detects a material gap and therefore closes the old
-- execution path without rewriting any earlier history.
INSERT INTO architecture_core.evidence_record (
    tenant_record_id,
    evidence_record_id,
    evidence_uri,
    sha256_digest,
    source_locator
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196e200-1111-7111-8111-111111111191',
    'urn:cwl:tenant_001:ea_core:target_state_evidence:0196e200-1111-7111-8111-111111111191',
    'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc',
    'verification://target-state/gap-1'
);

PERFORM *
  FROM architecture_core.record_target_state_verification(
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      '0196e010-1111-7111-8111-111111111191',
      '0196e210-1111-7111-8111-111111111191',
      '2027-05-05T00:00:00Z',
      'keyverse:https://id.example/realms/cwl#target-state-verifier-123',
      'New production evidence shows the approved database target still has a material gap.',
      '0196e200-1111-7111-8111-111111111191',
      'gap_detected'
  );

INSERT INTO architecture_core.evidence_record (
    tenant_record_id,
    evidence_record_id,
    evidence_uri,
    sha256_digest,
    source_locator
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196e220-1111-7111-8111-111111111191',
    'urn:cwl:tenant_001:ea_core:target_state_replan:0196e220-1111-7111-8111-111111111191',
    'dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd',
    'decision://target-state/replan-1'
);

-- A surrounding transaction rollback must undo every mutation produced by the
-- command, including predecessor supersession and the transactional outbox row.
DO $$
DECLARE
  replacement_count integer;
  replan_count integer;
  event_count integer;
  predecessor_closed boolean;
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.record_target_state_replan(
          '0195d145-64e8-7f4f-8a23-a0cc784cb711',
          '0196e010-1111-7111-8111-111111111191',
          '0196e230-1111-7111-8111-111111111191',
          '0196e240-1111-7111-8111-111111111191',
          '0196e002-1111-7111-8111-111111111111',
          '0196e001-1111-7111-8111-111111111111',
          'database_target_state_rollback_probe',
          'Rollback probe replacement',
          'This replacement must disappear with its surrounding transaction.',
          '2027-05-06T00:00:00Z',
          'keyverse:https://id.example/realms/cwl#target-state-replanner-123',
          'Prove replan history and outbox evidence share the caller transaction.',
          '0196e220-1111-7111-8111-111111111191'
      );
    RAISE EXCEPTION 'intentional replan rollback probe';
  EXCEPTION WHEN raise_exception THEN
    NULL;
  END;

  SELECT count(*) INTO replacement_count
    FROM architecture_core.architecture_transformation
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e230-1111-7111-8111-111111111191';
  SELECT count(*) INTO replan_count
    FROM architecture_core.transformation_replan_record
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND decision_request_id = '0196e240-1111-7111-8111-111111111191';
  SELECT count(*) INTO event_count
    FROM architecture_core.outbox_event
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND decision_request_id = '0196e240-1111-7111-8111-111111111191';
  SELECT superseded_at IS NOT NULL INTO predecessor_closed
    FROM architecture_core.architecture_transformation
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e010-1111-7111-8111-111111111191';

  IF replacement_count <> 0
     OR replan_count <> 0
     OR event_count <> 0
     OR predecessor_closed THEN
    RAISE EXCEPTION 'rolled-back replan left partial architecture or outbox state';
  END IF;
END;
$$;

CREATE TEMP TABLE replan_receipt AS
SELECT *
  FROM architecture_core.record_target_state_replan(
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      '0196e010-1111-7111-8111-111111111191',
      '0196e250-1111-7111-8111-111111111191',
      '0196e260-1111-7111-8111-111111111191',
      '0196e002-1111-7111-8111-111111111111',
      '0196e001-1111-7111-8111-111111111111',
      'database_target_state_v2',
      'Replanned database target state',
      'Replace the gap-detected database target with a governed second target.',
      '2027-05-06T00:00:00Z',
      'keyverse:https://id.example/realms/cwl#target-state-replanner-123',
      'The verified gap requires a distinct replacement before execution resumes.',
      '0196e220-1111-7111-8111-111111111191'
  );

DO $$
DECLARE
  replayed_flag boolean;
  buyer_next_action text;
  predecessor_closed boolean;
  replacement_count integer;
  history_count integer;
  replan_count integer;
  event_count integer;
  leaked_private_context boolean;
BEGIN
  SELECT replan_replayed, next_action
    INTO replayed_flag, buyer_next_action
    FROM replan_receipt;
  IF replayed_flag OR buyer_next_action <> 'approve_target_state' THEN
    RAISE EXCEPTION 'fresh target-state replan did not return the approval action';
  END IF;

  SELECT superseded_at IS NOT NULL INTO predecessor_closed
    FROM architecture_core.architecture_transformation
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e010-1111-7111-8111-111111111191';
  IF NOT predecessor_closed THEN
    RAISE EXCEPTION 'gap-detected predecessor was not closed in system time';
  END IF;

  SELECT count(*) INTO replacement_count
    FROM architecture_core.architecture_transformation
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e250-1111-7111-8111-111111111191'
     AND architecture_scenario_id = '0196e002-1111-7111-8111-111111111111'
     AND remediation_initiative_id = '0196e001-1111-7111-8111-111111111111'
     AND transformation_code = 'database_target_state_v2'
     AND truth_status_code = 'authoritative'
     AND evidence_record_id = '0196e220-1111-7111-8111-111111111191';
  SELECT count(*) INTO history_count
    FROM architecture_core.transformation_history_record
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e250-1111-7111-8111-111111111191'
     AND sequence_number = 1
     AND transformation_state_code = 'proposed'
     AND truth_status_code = 'authoritative'
     AND decision_request_id = '0196e260-1111-7111-8111-111111111191';
  SELECT count(*) INTO replan_count
    FROM architecture_core.transformation_replan_record
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND predecessor_architecture_transformation_id = '0196e010-1111-7111-8111-111111111191'
     AND replacement_architecture_transformation_id = '0196e250-1111-7111-8111-111111111191'
     AND decision_request_id = '0196e260-1111-7111-8111-111111111191'
     AND truth_status_code = 'authoritative';
  SELECT count(*) INTO event_count
    FROM architecture_core.outbox_event
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND architecture_transformation_id = '0196e250-1111-7111-8111-111111111191'
     AND decision_request_id = '0196e260-1111-7111-8111-111111111191'
     AND event_type_code = 'org.contextualwisdomlab.ea.transformation.replanned.v1'
     AND publish_status_code = 'pending';

  IF replacement_count <> 1 OR history_count <> 1 OR replan_count <> 1 OR event_count <> 1 THEN
    RAISE EXCEPTION 'replan did not atomically create exactly one replacement evidence chain';
  END IF;

  SELECT EXISTS (
      SELECT 1
        FROM architecture_core.outbox_event
       WHERE decision_request_id = '0196e260-1111-7111-8111-111111111191'
         AND (
           event_payload_json ? 'decision_actor_ref'
           OR event_payload_json ? 'decision_reason_text'
           OR event_payload_json ? 'transformation_description'
         )
  ) INTO leaked_private_context;
  IF leaked_private_context THEN
    RAISE EXCEPTION 'replan event leaked private or unnecessary raw context';
  END IF;
END;
$$;

-- Exact delivery replay must return the original immutable evidence identities
-- without duplicating the replacement, history, relationship, or outbox row.
DROP TABLE replan_receipt;
CREATE TEMP TABLE replan_receipt AS
SELECT *
  FROM architecture_core.record_target_state_replan(
      '0195d145-64e8-7f4f-8a23-a0cc784cb711',
      '0196e010-1111-7111-8111-111111111191',
      '0196e250-1111-7111-8111-111111111191',
      '0196e260-1111-7111-8111-111111111191',
      '0196e002-1111-7111-8111-111111111111',
      '0196e001-1111-7111-8111-111111111111',
      'database_target_state_v2',
      'Replanned database target state',
      'Replace the gap-detected database target with a governed second target.',
      '2027-05-06T00:00:00Z',
      'keyverse:https://id.example/realms/cwl#target-state-replanner-123',
      'The verified gap requires a distinct replacement before execution resumes.',
      '0196e220-1111-7111-8111-111111111191'
  );

DO $$
DECLARE
  replayed_flag boolean;
  replacement_count integer;
  history_count integer;
  replan_count integer;
  event_count integer;
BEGIN
  SELECT replan_replayed INTO replayed_flag FROM replan_receipt;
  IF NOT replayed_flag THEN
    RAISE EXCEPTION 'exact target-state replan replay was not idempotent';
  END IF;

  SELECT count(*) INTO replacement_count
    FROM architecture_core.architecture_transformation
   WHERE architecture_transformation_id = '0196e250-1111-7111-8111-111111111191';
  SELECT count(*) INTO history_count
    FROM architecture_core.transformation_history_record
   WHERE decision_request_id = '0196e260-1111-7111-8111-111111111191';
  SELECT count(*) INTO replan_count
    FROM architecture_core.transformation_replan_record
   WHERE decision_request_id = '0196e260-1111-7111-8111-111111111191';
  SELECT count(*) INTO event_count
    FROM architecture_core.outbox_event
   WHERE decision_request_id = '0196e260-1111-7111-8111-111111111191';

  IF replacement_count <> 1 OR history_count <> 1 OR replan_count <> 1 OR event_count <> 1 THEN
    RAISE EXCEPTION 'replan replay duplicated immutable evidence';
  END IF;
END;
$$;

-- Reusing the same decision id with different meaning must fail closed.
DO $$
DECLARE
  conflict_rejected boolean := false;
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.record_target_state_replan(
          '0195d145-64e8-7f4f-8a23-a0cc784cb711',
          '0196e010-1111-7111-8111-111111111191',
          '0196e250-1111-7111-8111-111111111191',
          '0196e260-1111-7111-8111-111111111191',
          '0196e002-1111-7111-8111-111111111111',
          '0196e001-1111-7111-8111-111111111111',
          'database_target_state_v2',
          'Conflicting replacement title',
          'Replace the gap-detected database target with a governed second target.',
          '2027-05-06T00:00:00Z',
          'keyverse:https://id.example/realms/cwl#target-state-replanner-123',
          'The verified gap requires a distinct replacement before execution resumes.',
          '0196e220-1111-7111-8111-111111111191'
      );
  EXCEPTION WHEN unique_violation THEN
    conflict_rejected := true;
  END;
  IF NOT conflict_rejected THEN
    RAISE EXCEPTION 'conflicting target-state replan replay was accepted';
  END IF;
END;
$$;

-- Replan relationship evidence is immutable after commit.
DO $$
DECLARE
  mutation_rejected boolean := false;
BEGIN
  BEGIN
    UPDATE architecture_core.transformation_replan_record
       SET effective_at = effective_at + interval '1 second'
     WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND decision_request_id = '0196e260-1111-7111-8111-111111111191';
  EXCEPTION WHEN check_violation THEN
    mutation_rejected := true;
  END;
  IF NOT mutation_rejected THEN
    RAISE EXCEPTION 'immutable target-state replan evidence was mutable';
  END IF;
END;
$$;

-- A transformation that is not gap-detected cannot be used as a replan
-- predecessor, and the rejected command must not create replacement evidence.
DO $$
DECLARE
  wrong_state_rejected boolean := false;
  leaked_rows integer;
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.record_target_state_replan(
          '0195d145-64e8-7f4f-8a23-a0cc784cb711',
          '0196e250-1111-7111-8111-111111111191',
          '0196e270-1111-7111-8111-111111111191',
          '0196e280-1111-7111-8111-111111111191',
          '0196e002-1111-7111-8111-111111111111',
          '0196e001-1111-7111-8111-111111111111',
          'database_target_state_v3',
          'Invalid premature replan',
          'A proposed target must not be silently replaced as though it had a detected gap.',
          '2027-05-07T00:00:00Z',
          'keyverse:https://id.example/realms/cwl#target-state-replanner-123',
          'This request must fail because the predecessor is only proposed.',
          '0196e220-1111-7111-8111-111111111191'
      );
  EXCEPTION WHEN check_violation THEN
    wrong_state_rejected := true;
  END;
  SELECT count(*) INTO leaked_rows
    FROM architecture_core.architecture_transformation
   WHERE architecture_transformation_id = '0196e270-1111-7111-8111-111111111191';
  IF NOT wrong_state_rejected OR leaked_rows <> 0 THEN
    RAISE EXCEPTION 'non-gap predecessor produced replacement state';
  END IF;
END;
$$;

-- Composite tenant/object identity prevents a different tenant from resolving
-- this predecessor or creating a cross-tenant replacement relationship.
DO $$
DECLARE
  cross_tenant_rejected boolean := false;
BEGIN
  BEGIN
    PERFORM *
      FROM architecture_core.record_target_state_replan(
          '0195d145-64e8-7f4f-8a23-a0cc784cb799',
          '0196e010-1111-7111-8111-111111111191',
          '0196e290-1111-7111-8111-111111111191',
          '0196e2a0-1111-7111-8111-111111111191',
          '0196e002-1111-7111-8111-111111111111',
          '0196e001-1111-7111-8111-111111111111',
          'database_target_state_cross_tenant',
          'Cross-tenant replacement',
          'A foreign tenant must not resolve or replace this predecessor.',
          '2027-05-07T00:00:00Z',
          'keyverse:https://id.example/realms/cwl#target-state-replanner-foreign',
          'Cross-tenant replan attempt must fail closed.',
          '0196e220-1111-7111-8111-111111111191'
      );
  EXCEPTION WHEN check_violation THEN
    cross_tenant_rejected := true;
  END;
  IF NOT cross_tenant_rejected THEN
    RAISE EXCEPTION 'cross-tenant target-state replan was accepted';
  END IF;
END;
$$;
