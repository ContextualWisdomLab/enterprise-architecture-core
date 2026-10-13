\set ON_ERROR_STOP on

-- Buyer acceptance for versioned strategy execution. The first branch commit
-- required these tables before migration 0011 existed and produced a hosted
-- RED failure at this exact missing-table boundary.

DO $$
DECLARE
  missing_table_count integer;
BEGIN
  SELECT count(*)
    INTO missing_table_count
    FROM (VALUES
      ('strategy_objective'),
      ('remediation_initiative'),
      ('initiative_objective_link'),
      ('initiative_milestone')
    ) AS required_table(table_name)
   WHERE to_regclass('architecture_core.' || required_table.table_name) IS NULL;

  IF missing_table_count <> 0 THEN
    RAISE EXCEPTION 'strategy execution tables missing: %', missing_table_count;
  END IF;
END;
$$;

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.strategy_objective (
        tenant_record_id,
        strategy_objective_id,
        objective_code,
        objective_title,
        valid_from,
        valid_to,
        truth_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196b001-1111-7111-8111-111111111110',
        'reduce_platform_risk',
        'Reduce platform risk',
        '2026-01-01T00:00:00Z',
        '2028-01-01T00:00:00Z',
        'authoritative'
    );
    RAISE EXCEPTION 'authoritative objective without evidence was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

INSERT INTO architecture_core.strategy_objective (
    tenant_record_id,
    strategy_objective_id,
    objective_code,
    objective_title,
    objective_description,
    valid_from,
    valid_to,
    truth_status_code,
    evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196b001-1111-7111-8111-111111111111',
    'reduce_platform_risk',
    'Reduce platform risk',
    'Remove unsupported database technology from critical applications.',
    '2026-01-01T00:00:00Z',
    '2028-01-01T00:00:00Z',
    'authoritative',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
);

INSERT INTO architecture_core.remediation_initiative (
    tenant_record_id,
    remediation_initiative_id,
    initiative_code,
    initiative_title,
    initiative_description,
    valid_from,
    valid_to,
    truth_status_code,
    evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196b002-1111-7111-8111-111111111111',
    'modernize_order_database',
    'Modernize order database',
    'Replace the unsupported database while preserving the application boundary.',
    '2026-04-01T00:00:00Z',
    '2027-10-01T00:00:00Z',
    'authoritative',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
);

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.initiative_objective_link (
        tenant_record_id,
        initiative_objective_link_id,
        remediation_initiative_id,
        strategy_objective_id,
        contribution_type_code,
        valid_from,
        valid_to,
        truth_status_code,
        evidence_record_id
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196b003-1111-7111-8111-111111111110',
        '0196b002-1111-7111-8111-111111111111',
        '0196b001-1111-7111-8111-111111111111',
        'advances_objective',
        '2026-03-01T00:00:00Z',
        '2027-10-01T00:00:00Z',
        'authoritative',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    );
    RAISE EXCEPTION 'link validity outside initiative was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

INSERT INTO architecture_core.initiative_objective_link (
    tenant_record_id,
    initiative_objective_link_id,
    remediation_initiative_id,
    strategy_objective_id,
    contribution_type_code,
    valid_from,
    valid_to,
    truth_status_code,
    evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196b003-1111-7111-8111-111111111111',
    '0196b002-1111-7111-8111-111111111111',
    '0196b001-1111-7111-8111-111111111111',
    'advances_objective',
    '2026-04-01T00:00:00Z',
    '2027-10-01T00:00:00Z',
    'authoritative',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
);

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.initiative_milestone (
        tenant_record_id,
        initiative_milestone_id,
        remediation_initiative_id,
        milestone_code,
        milestone_title,
        sequence_number,
        target_at,
        valid_from,
        valid_to,
        truth_status_code,
        evidence_record_id
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196b004-1111-7111-8111-111111111110',
        '0196b002-1111-7111-8111-111111111111',
        'target_state_ready',
        'Target-state database ready',
        1,
        '2028-02-01T00:00:00Z',
        '2026-04-01T00:00:00Z',
        '2027-10-01T00:00:00Z',
        'authoritative',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    );
    RAISE EXCEPTION 'milestone target outside initiative was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.initiative_milestone (
        tenant_record_id,
        initiative_milestone_id,
        remediation_initiative_id,
        milestone_code,
        milestone_title,
        sequence_number,
        target_at,
        valid_from,
        valid_to,
        truth_status_code,
        evidence_record_id
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196b004-1111-7111-8111-111111111112',
        '0196b002-1111-7111-8111-111111111111',
        'target_state_ready',
        'Target-state database ready',
        0,
        '2026-10-01T00:00:00Z',
        '2026-04-01T00:00:00Z',
        '2027-10-01T00:00:00Z',
        'authoritative',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    );
    RAISE EXCEPTION 'non-positive milestone sequence was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

INSERT INTO architecture_core.initiative_milestone (
    tenant_record_id,
    initiative_milestone_id,
    remediation_initiative_id,
    milestone_code,
    milestone_title,
    milestone_description,
    sequence_number,
    target_at,
    valid_from,
    valid_to,
    truth_status_code,
    evidence_record_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0196b004-1111-7111-8111-111111111111',
    '0196b002-1111-7111-8111-111111111111',
    'target_state_ready',
    'Target-state database ready',
    'Approved target technology is installable before migration execution.',
    1,
    '2026-10-01T00:00:00Z',
    '2026-04-01T00:00:00Z',
    '2027-10-01T00:00:00Z',
    'authoritative',
    '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
);

DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.strategy_objective
       SET objective_title = 'Retrospectively rewritten objective'
     WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND strategy_objective_id = '0196b001-1111-7111-8111-111111111111';
    RAISE EXCEPTION 'strategy objective meaning was mutable';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.initiative_milestone
       SET target_at = '2027-03-01T00:00:00Z'
     WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND initiative_milestone_id = '0196b004-1111-7111-8111-111111111111';
    RAISE EXCEPTION 'milestone decision meaning was mutable';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

UPDATE architecture_core.remediation_initiative
   SET superseded_at = clock_timestamp()
 WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
   AND remediation_initiative_id = '0196b002-1111-7111-8111-111111111111';

DO $$
BEGIN
  BEGIN
    UPDATE architecture_core.remediation_initiative
       SET superseded_at = superseded_at + interval '1 second'
     WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb711'
       AND remediation_initiative_id = '0196b002-1111-7111-8111-111111111111';
    RAISE EXCEPTION 'strategy supersession timestamp was mutable';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

SET ROLE ea_runtime;
SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
DECLARE
  visible_objective_count integer;
BEGIN
  SELECT count(*)
    INTO visible_objective_count
    FROM architecture_core.strategy_objective;
  IF visible_objective_count <> 1 THEN
    RAISE EXCEPTION
      'strategy objective tenant isolation exposed % rows',
      visible_objective_count;
  END IF;
END;
$$;

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.strategy_objective (
        tenant_record_id,
        strategy_objective_id,
        objective_code,
        objective_title,
        valid_from,
        truth_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb712',
        '0196b001-1111-7111-8111-111111111112',
        'foreign_tenant_objective',
        'Foreign tenant objective',
        '2026-01-01T00:00:00Z',
        'inferred'
    );
    RAISE EXCEPTION 'cross-tenant strategy insert unexpectedly succeeded';
  EXCEPTION WHEN insufficient_privilege THEN
    NULL;
  END;
END;
$$;

RESET ROLE;
