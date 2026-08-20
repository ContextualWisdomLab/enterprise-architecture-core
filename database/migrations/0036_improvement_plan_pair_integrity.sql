BEGIN;

ALTER TABLE architecture_core.initiative_milestone
    ADD CONSTRAINT initiative_milestone_identity_initiative_unique
    UNIQUE (
        tenant_record_id,
        initiative_milestone_id,
        remediation_initiative_id
    );

ALTER TABLE architecture_core.assessment_improvement_plan
    DROP CONSTRAINT assessment_improvement_plan_milestone_foreign;

ALTER TABLE architecture_core.assessment_improvement_plan
    ADD CONSTRAINT assessment_improvement_plan_milestone_initiative_foreign
    FOREIGN KEY (
        tenant_record_id,
        initiative_milestone_id,
        remediation_initiative_id
    )
    REFERENCES architecture_core.initiative_milestone (
        tenant_record_id,
        initiative_milestone_id,
        remediation_initiative_id
    );

COMMENT ON CONSTRAINT assessment_improvement_plan_milestone_initiative_foreign
ON architecture_core.assessment_improvement_plan IS
'Preserves one relational fact: the milestone recorded by an assessment improvement plan must belong to the same remediation initiative recorded by that plan.';

CREATE TABLE architecture_core.assessment_improvement_dependency_set (
    tenant_record_id uuid NOT NULL,
    assessment_improvement_plan_id uuid NOT NULL,
    dependency_count integer NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT assessment_improvement_dependency_set_primary_key
        PRIMARY KEY (tenant_record_id, assessment_improvement_plan_id),
    CONSTRAINT assessment_improvement_dependency_set_plan_foreign
        FOREIGN KEY (tenant_record_id, assessment_improvement_plan_id)
        REFERENCES architecture_core.assessment_improvement_plan
            (tenant_record_id, assessment_improvement_plan_id),
    CONSTRAINT assessment_improvement_dependency_set_count_bounds
        CHECK (dependency_count BETWEEN 0 AND 32)
);

CREATE TABLE architecture_core.assessment_improvement_dependency_relation (
    tenant_record_id uuid NOT NULL,
    assessment_improvement_plan_id uuid NOT NULL,
    prerequisite_initiative_id uuid NOT NULL,
    dependency_evidence_record_id uuid NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    CONSTRAINT assessment_improvement_dependency_relation_primary_key
        PRIMARY KEY (
            tenant_record_id,
            assessment_improvement_plan_id,
            prerequisite_initiative_id
        ),
    CONSTRAINT assessment_improvement_dependency_relation_plan_foreign
        FOREIGN KEY (tenant_record_id, assessment_improvement_plan_id)
        REFERENCES architecture_core.assessment_improvement_plan
            (tenant_record_id, assessment_improvement_plan_id),
    CONSTRAINT assessment_improvement_dependency_relation_initiative_foreign
        FOREIGN KEY (tenant_record_id, prerequisite_initiative_id)
        REFERENCES architecture_core.remediation_initiative
            (tenant_record_id, remediation_initiative_id),
    CONSTRAINT assessment_improvement_dependency_relation_evidence_foreign
        FOREIGN KEY (tenant_record_id, dependency_evidence_record_id)
        REFERENCES architecture_core.evidence_record
            (tenant_record_id, evidence_record_id)
);

ALTER TABLE architecture_core.assessment_improvement_dependency_set
    ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.assessment_improvement_dependency_set
    FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy
ON architecture_core.assessment_improvement_dependency_set
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.assessment_improvement_dependency_relation
    ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.assessment_improvement_dependency_relation
    FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy
ON architecture_core.assessment_improvement_dependency_relation
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

CREATE INDEX assessment_improvement_dependency_prerequisite_index
    ON architecture_core.assessment_improvement_dependency_relation
        (tenant_record_id, prerequisite_initiative_id, recorded_at DESC);

CREATE TRIGGER assessment_improvement_dependency_set_mutation_guard
BEFORE UPDATE OR DELETE
ON architecture_core.assessment_improvement_dependency_set
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_assessment_improvement_plan_mutation();

CREATE TRIGGER assessment_improvement_dependency_relation_mutation_guard
BEFORE UPDATE OR DELETE
ON architecture_core.assessment_improvement_dependency_relation
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_assessment_improvement_plan_mutation();

CREATE FUNCTION architecture_core.create_data_management_improvement_plan(
    requested_assessment_projection_id uuid,
    requested_missing_evidence_code text,
    requested_decision_request_id uuid,
    requested_target_capability_object_id uuid,
    requested_accountable_organization_object_id uuid,
    requested_initiative_code text,
    requested_initiative_title text,
    requested_milestone_code text,
    requested_milestone_title text,
    requested_due_at timestamptz,
    requested_funding_reference text,
    requested_prerequisite_initiative_ids uuid[],
    requested_dependency_evidence_record_ids uuid[]
)
RETURNS TABLE (
    assessment_improvement_plan_id uuid,
    remediation_initiative_id uuid,
    initiative_milestone_id uuid,
    outbox_event_id uuid
)
LANGUAGE plpgsql
VOLATILE
SECURITY DEFINER
SET search_path = pg_catalog
AS $$
DECLARE
  active_tenant_id uuid;
  requested_dependency_count integer;
  requested_evidence_count integer;
  existing_plan_id uuid;
  stored_dependency_count integer;
  result_plan_id uuid;
  result_initiative_id uuid;
  result_milestone_id uuid;
  result_event_id uuid;
BEGIN
  active_tenant_id := architecture_core.current_tenant_id();
  IF active_tenant_id IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'verified tenant context is required for assessment improvement dependencies';
  END IF;

  IF requested_prerequisite_initiative_ids IS NULL
     OR requested_dependency_evidence_record_ids IS NULL THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'dependency initiatives and dependency evidence arrays are required; use empty arrays for no dependencies';
  END IF;

  requested_dependency_count := pg_catalog.cardinality(
      requested_prerequisite_initiative_ids
  );
  requested_evidence_count := pg_catalog.cardinality(
      requested_dependency_evidence_record_ids
  );

  IF requested_dependency_count <> requested_evidence_count
     OR requested_dependency_count > 32 THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'dependency initiatives and evidence must be aligned one-to-one and contain at most 32 items';
  END IF;

  IF EXISTS (
      SELECT 1
        FROM pg_catalog.unnest(requested_prerequisite_initiative_ids) AS prerequisite_id
       WHERE prerequisite_id IS NULL
          OR uuid_extract_version(prerequisite_id) <> 7
  )
     OR EXISTS (
      SELECT 1
        FROM pg_catalog.unnest(requested_dependency_evidence_record_ids) AS evidence_id
       WHERE evidence_id IS NULL
          OR uuid_extract_version(evidence_id) <> 7
  ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'dependency initiatives and evidence require canonical UUIDv7 identities';
  END IF;

  IF (
      SELECT count(DISTINCT prerequisite_id)
        FROM pg_catalog.unnest(requested_prerequisite_initiative_ids) AS prerequisite_id
     ) <> requested_dependency_count THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'dependency initiative identities must be unique within one improvement decision';
  END IF;

  IF EXISTS (
      SELECT 1
        FROM pg_catalog.unnest(requested_dependency_evidence_record_ids) AS evidence_id
       WHERE NOT EXISTS (
          SELECT 1
            FROM architecture_core.evidence_record AS evidence_record
           WHERE evidence_record.tenant_record_id = active_tenant_id
             AND evidence_record.evidence_record_id = evidence_id
       )
  ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'every prerequisite requires tenant-scoped dependency evidence';
  END IF;

  -- Own the source-assessment serialization point before checking mutable
  -- prerequisite liveness. This makes the decision linearizable with concurrent
  -- assessment deliveries and prevents a prerequisite from being superseded
  -- while this command waits to acquire the source aggregate.
  PERFORM 1
    FROM architecture_core.data_management_assessment_projection AS projection_record
   WHERE projection_record.tenant_record_id = active_tenant_id
     AND projection_record.data_management_assessment_projection_id =
         requested_assessment_projection_id
   FOR UPDATE;

  IF NOT FOUND THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'assessment projection is unavailable for the verified tenant';
  END IF;

  -- Lock every existing requested prerequisite in deterministic UUID order before
  -- evaluating supersession. Different source assessments can share prerequisites;
  -- deterministic lock order prevents dependency-set lock cycles while FOR UPDATE
  -- prevents a concurrent supersession from invalidating the accepted decision.
  PERFORM initiative_record.remediation_initiative_id
    FROM architecture_core.remediation_initiative AS initiative_record
    JOIN pg_catalog.unnest(requested_prerequisite_initiative_ids)
         AS requested_prerequisite(prerequisite_initiative_id)
      ON requested_prerequisite.prerequisite_initiative_id =
         initiative_record.remediation_initiative_id
   WHERE initiative_record.tenant_record_id = active_tenant_id
   ORDER BY initiative_record.remediation_initiative_id
   FOR UPDATE OF initiative_record;

  IF EXISTS (
      SELECT 1
        FROM pg_catalog.unnest(requested_prerequisite_initiative_ids) AS prerequisite_id
       WHERE NOT EXISTS (
          SELECT 1
            FROM architecture_core.remediation_initiative AS initiative_record
           WHERE initiative_record.tenant_record_id = active_tenant_id
             AND initiative_record.remediation_initiative_id = prerequisite_id
             AND initiative_record.superseded_at IS NULL
             AND initiative_record.truth_status_code NOT IN ('rejected', 'superseded')
       )
  ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'every prerequisite must reference an active remediation initiative in the verified tenant';
  END IF;

  SELECT plan_record.assessment_improvement_plan_id
    INTO existing_plan_id
    FROM architecture_core.assessment_improvement_plan AS plan_record
   WHERE plan_record.tenant_record_id = active_tenant_id
     AND plan_record.decision_request_id = requested_decision_request_id;

  IF existing_plan_id IS NOT NULL THEN
    SELECT dependency_set.dependency_count
      INTO stored_dependency_count
      FROM architecture_core.assessment_improvement_dependency_set AS dependency_set
     WHERE dependency_set.tenant_record_id = active_tenant_id
       AND dependency_set.assessment_improvement_plan_id = existing_plan_id;

    IF stored_dependency_count IS NULL THEN
      RAISE EXCEPTION USING
        ERRCODE = '23505',
        MESSAGE = 'decision request id was recorded without the dependency-aware contract';
    END IF;

    IF stored_dependency_count <> requested_dependency_count
       OR EXISTS (
          (
            SELECT
                requested_prerequisite_initiative_ids[pair_index] AS prerequisite_id,
                requested_dependency_evidence_record_ids[pair_index] AS evidence_id
              FROM pg_catalog.generate_subscripts(
                  requested_prerequisite_initiative_ids,
                  1
              ) AS pair_index
            EXCEPT
            SELECT
                dependency_relation.prerequisite_initiative_id,
                dependency_relation.dependency_evidence_record_id
              FROM architecture_core.assessment_improvement_dependency_relation
                  AS dependency_relation
             WHERE dependency_relation.tenant_record_id = active_tenant_id
               AND dependency_relation.assessment_improvement_plan_id = existing_plan_id
          )
          UNION ALL
          (
            SELECT
                dependency_relation.prerequisite_initiative_id,
                dependency_relation.dependency_evidence_record_id
              FROM architecture_core.assessment_improvement_dependency_relation
                  AS dependency_relation
             WHERE dependency_relation.tenant_record_id = active_tenant_id
               AND dependency_relation.assessment_improvement_plan_id = existing_plan_id
            EXCEPT
            SELECT
                requested_prerequisite_initiative_ids[pair_index] AS prerequisite_id,
                requested_dependency_evidence_record_ids[pair_index] AS evidence_id
              FROM pg_catalog.generate_subscripts(
                  requested_prerequisite_initiative_ids,
                  1
              ) AS pair_index
          )
       ) THEN
      RAISE EXCEPTION USING
        ERRCODE = '23505',
        MESSAGE = 'decision request id already represents a different dependency set';
    END IF;
  END IF;

  SELECT
      result.assessment_improvement_plan_id,
      result.remediation_initiative_id,
      result.initiative_milestone_id,
      result.outbox_event_id
    INTO
      result_plan_id,
      result_initiative_id,
      result_milestone_id,
      result_event_id
    FROM architecture_core.create_data_management_improvement_plan(
      requested_assessment_projection_id,
      requested_missing_evidence_code,
      requested_decision_request_id,
      requested_target_capability_object_id,
      requested_accountable_organization_object_id,
      requested_initiative_code,
      requested_initiative_title,
      requested_milestone_code,
      requested_milestone_title,
      requested_due_at,
      requested_funding_reference
    ) AS result;

  IF existing_plan_id IS NULL THEN
    INSERT INTO architecture_core.assessment_improvement_dependency_set (
        tenant_record_id,
        assessment_improvement_plan_id,
        dependency_count
    ) VALUES (
        active_tenant_id,
        result_plan_id,
        requested_dependency_count
    );

    INSERT INTO architecture_core.assessment_improvement_dependency_relation (
        tenant_record_id,
        assessment_improvement_plan_id,
        prerequisite_initiative_id,
        dependency_evidence_record_id
    )
    SELECT
        active_tenant_id,
        result_plan_id,
        requested_prerequisite_initiative_ids[pair_index],
        requested_dependency_evidence_record_ids[pair_index]
      FROM pg_catalog.generate_subscripts(
          requested_prerequisite_initiative_ids,
          1
      ) AS pair_index;
  END IF;

  RETURN QUERY
  SELECT
      result_plan_id,
      result_initiative_id,
      result_milestone_id,
      result_event_id;
END;
$$;

REVOKE ALL
ON FUNCTION architecture_core.create_data_management_improvement_plan(
    uuid,
    text,
    uuid,
    uuid,
    uuid,
    text,
    text,
    text,
    text,
    timestamptz,
    text,
    uuid[],
    uuid[]
)
FROM PUBLIC;

COMMENT ON TABLE architecture_core.assessment_improvement_dependency_set IS
'Immutable declaration that one assessment-improvement decision supplied an explicit bounded dependency set, including the meaningful empty set. It distinguishes exact replay from legacy calls that did not provide dependency semantics.';

COMMENT ON TABLE architecture_core.assessment_improvement_dependency_relation IS
'Normalized immutable EA-owned evidence for one prerequisite initiative of an assessment-driven remediation plan. Each dependency carries tenant-scoped evidence and remains proposed decision context rather than foreign assessment authority.';

COMMENT ON FUNCTION architecture_core.create_data_management_improvement_plan(
    uuid,
    text,
    uuid,
    uuid,
    uuid,
    text,
    text,
    text,
    text,
    timestamptz,
    text,
    uuid[],
    uuid[]
) IS
'Creates or exactly replays an assessment-driven proposed remediation plan with an explicit dependency set. Prerequisite initiatives and one-to-one evidence are bounded, tenant-scoped, immutable, and replay-checked; source and prerequisite locks make concurrent acceptance linearizable with supersession. The underlying assessment projection remains read-only foreign evidence.';

COMMIT;
