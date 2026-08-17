\set ON_ERROR_STOP on

-- A proposed target state cannot be promoted merely by attaching an
-- authoritative transformation record to it.
DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.remediation_initiative (
        tenant_record_id,
        remediation_initiative_id,
        initiative_code,
        initiative_title,
        valid_from,
        valid_to,
        truth_status_code,
        evidence_record_id
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e100-1111-7111-8111-111111111111',
        'authority_boundary_initiative',
        'Authority boundary initiative',
        '2026-08-01T00:00:00Z',
        '2028-01-01T00:00:00Z',
        'authoritative',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    );

    INSERT INTO architecture_core.architecture_scenario (
        tenant_record_id,
        architecture_scenario_id,
        scenario_code,
        scenario_title,
        target_valid_at,
        valid_from,
        valid_to,
        truth_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e101-1111-7111-8111-111111111111',
        'proposed_authority_target',
        'Proposed authority target',
        '2027-12-01T00:00:00Z',
        '2026-08-01T00:00:00Z',
        '2028-01-01T00:00:00Z',
        'proposed'
    );

    INSERT INTO architecture_core.scenario_baseline (
        tenant_record_id,
        scenario_baseline_id,
        architecture_scenario_id,
        baseline_valid_at,
        baseline_recorded_at,
        recorded_at
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e102-1111-7111-8111-111111111111',
        '0196e101-1111-7111-8111-111111111111',
        '2026-07-01T00:00:00Z',
        '2026-08-01T00:00:00Z',
        '2026-08-01T00:00:01Z'
    );

    INSERT INTO architecture_core.architecture_transformation (
        tenant_record_id,
        architecture_transformation_id,
        architecture_scenario_id,
        remediation_initiative_id,
        transformation_code,
        transformation_title,
        valid_from,
        valid_to,
        recorded_at,
        truth_status_code,
        evidence_record_id
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e103-1111-7111-8111-111111111111',
        '0196e101-1111-7111-8111-111111111111',
        '0196e100-1111-7111-8111-111111111111',
        'proposed_target_promotion',
        'Proposed target promotion',
        '2026-08-01T00:00:00Z',
        '2028-01-01T00:00:00Z',
        '2026-08-02T00:00:00Z',
        'authoritative',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    );

    RAISE EXCEPTION 'authoritative transformation promoted a proposed scenario';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;

-- An authoritative approval event cannot promote a transformation whose own
-- truth status is still proposed.
DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.remediation_initiative (
        tenant_record_id,
        remediation_initiative_id,
        initiative_code,
        initiative_title,
        valid_from,
        valid_to,
        truth_status_code,
        evidence_record_id
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e110-1111-7111-8111-111111111111',
        'proposed_transform_initiative',
        'Proposed transformation initiative',
        '2026-08-01T00:00:00Z',
        '2028-01-01T00:00:00Z',
        'authoritative',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    );

    INSERT INTO architecture_core.architecture_scenario (
        tenant_record_id,
        architecture_scenario_id,
        scenario_code,
        scenario_title,
        target_valid_at,
        valid_from,
        valid_to,
        truth_status_code,
        evidence_record_id
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e111-1111-7111-8111-111111111111',
        'authoritative_history_target',
        'Authoritative history target',
        '2027-12-01T00:00:00Z',
        '2026-08-01T00:00:00Z',
        '2028-01-01T00:00:00Z',
        'authoritative',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    );

    INSERT INTO architecture_core.scenario_baseline (
        tenant_record_id,
        scenario_baseline_id,
        architecture_scenario_id,
        baseline_valid_at,
        baseline_recorded_at,
        recorded_at
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e112-1111-7111-8111-111111111111',
        '0196e111-1111-7111-8111-111111111111',
        '2026-07-01T00:00:00Z',
        '2026-08-01T00:00:00Z',
        '2026-08-01T00:00:01Z'
    );

    INSERT INTO architecture_core.architecture_transformation (
        tenant_record_id,
        architecture_transformation_id,
        architecture_scenario_id,
        remediation_initiative_id,
        transformation_code,
        transformation_title,
        valid_from,
        valid_to,
        recorded_at,
        truth_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e113-1111-7111-8111-111111111111',
        '0196e111-1111-7111-8111-111111111111',
        '0196e110-1111-7111-8111-111111111111',
        'proposed_transform_state',
        'Proposed transform state',
        '2026-08-01T00:00:00Z',
        '2028-01-01T00:00:00Z',
        '2026-08-02T00:00:00Z',
        'proposed'
    );

    INSERT INTO architecture_core.transformation_history_record (
        tenant_record_id,
        transformation_history_record_id,
        architecture_transformation_id,
        sequence_number,
        transformation_state_code,
        effective_at,
        recorded_at,
        decision_actor_ref,
        decision_reason_text,
        truth_status_code
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e114-1111-7111-8111-111111111111',
        '0196e113-1111-7111-8111-111111111111',
        1,
        'proposed',
        '2026-09-01T00:00:00Z',
        '2026-09-01T01:00:00Z',
        'urn:cwl:actor:architecture-board',
        'The transformation itself is not yet authoritative.',
        'proposed'
    );

    INSERT INTO architecture_core.transformation_history_record (
        tenant_record_id,
        transformation_history_record_id,
        architecture_transformation_id,
        sequence_number,
        transformation_state_code,
        effective_at,
        recorded_at,
        decision_actor_ref,
        decision_reason_text,
        truth_status_code,
        evidence_record_id
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        '0196e115-1111-7111-8111-111111111111',
        '0196e113-1111-7111-8111-111111111111',
        2,
        'approved',
        '2026-10-01T00:00:00Z',
        '2026-09-20T00:00:00Z',
        'urn:cwl:actor:architecture-board',
        'Approval must not elevate a proposed transformation identity.',
        'authoritative',
        '0195d145-64e8-7f4f-8a23-a0cc784cbf10'
    );

    RAISE EXCEPTION 'approval promoted a proposed transformation';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END;
$$;
