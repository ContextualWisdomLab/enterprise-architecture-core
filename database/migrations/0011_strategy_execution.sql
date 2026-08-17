BEGIN;

CREATE TABLE architecture_core.strategy_objective (
    tenant_record_id uuid NOT NULL,
    strategy_objective_id uuid NOT NULL DEFAULT uuidv7(),
    objective_code text NOT NULL,
    objective_title text NOT NULL,
    objective_description text,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    superseded_at timestamptz,
    truth_status_code text NOT NULL,
    evidence_record_id uuid,
    CONSTRAINT strategy_objective_primary_key
        PRIMARY KEY (tenant_record_id, strategy_objective_id),
    CONSTRAINT strategy_objective_tenant_foreign
        FOREIGN KEY (tenant_record_id)
        REFERENCES architecture_core.tenant_record (tenant_record_id),
    CONSTRAINT strategy_objective_evidence_foreign
        FOREIGN KEY (tenant_record_id, evidence_record_id)
        REFERENCES architecture_core.evidence_record
            (tenant_record_id, evidence_record_id),
    CONSTRAINT strategy_objective_uuid_version
        CHECK (uuid_extract_version(strategy_objective_id) = 7),
    CONSTRAINT strategy_objective_code_format
        CHECK (objective_code ~ '^[a-z][a-z0-9]+(?:_[a-z0-9]+)*$'),
    CONSTRAINT strategy_objective_title_nonempty
        CHECK (length(btrim(objective_title)) > 0),
    CONSTRAINT strategy_objective_description_length
        CHECK (
            objective_description IS NULL
            OR length(objective_description) BETWEEN 1 AND 4096
        ),
    CONSTRAINT strategy_objective_valid_interval
        CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT strategy_objective_system_interval
        CHECK (superseded_at IS NULL OR superseded_at >= recorded_at),
    CONSTRAINT strategy_objective_truth_allowed
        CHECK (
            truth_status_code IN (
                'authoritative',
                'observed',
                'inferred',
                'proposed',
                'superseded',
                'rejected'
            )
        ),
    CONSTRAINT strategy_objective_evidence_required
        CHECK (
            truth_status_code NOT IN ('authoritative', 'observed')
            OR evidence_record_id IS NOT NULL
        ),
    CONSTRAINT strategy_objective_active_interval_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            objective_code WITH =,
            tstzrange(valid_from, valid_to, '[)') WITH &&
        ) WHERE (
            superseded_at IS NULL
            AND truth_status_code = 'authoritative'
        )
);

CREATE TABLE architecture_core.remediation_initiative (
    tenant_record_id uuid NOT NULL,
    remediation_initiative_id uuid NOT NULL DEFAULT uuidv7(),
    initiative_code text NOT NULL,
    initiative_title text NOT NULL,
    initiative_description text,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    superseded_at timestamptz,
    truth_status_code text NOT NULL,
    evidence_record_id uuid,
    CONSTRAINT remediation_initiative_primary_key
        PRIMARY KEY (tenant_record_id, remediation_initiative_id),
    CONSTRAINT remediation_initiative_tenant_foreign
        FOREIGN KEY (tenant_record_id)
        REFERENCES architecture_core.tenant_record (tenant_record_id),
    CONSTRAINT remediation_initiative_evidence_foreign
        FOREIGN KEY (tenant_record_id, evidence_record_id)
        REFERENCES architecture_core.evidence_record
            (tenant_record_id, evidence_record_id),
    CONSTRAINT remediation_initiative_uuid_version
        CHECK (uuid_extract_version(remediation_initiative_id) = 7),
    CONSTRAINT remediation_initiative_code_format
        CHECK (initiative_code ~ '^[a-z][a-z0-9]+(?:_[a-z0-9]+)*$'),
    CONSTRAINT remediation_initiative_title_nonempty
        CHECK (length(btrim(initiative_title)) > 0),
    CONSTRAINT remediation_initiative_description_length
        CHECK (
            initiative_description IS NULL
            OR length(initiative_description) BETWEEN 1 AND 4096
        ),
    CONSTRAINT remediation_initiative_valid_interval
        CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT remediation_initiative_system_interval
        CHECK (superseded_at IS NULL OR superseded_at >= recorded_at),
    CONSTRAINT remediation_initiative_truth_allowed
        CHECK (
            truth_status_code IN (
                'authoritative',
                'observed',
                'inferred',
                'proposed',
                'superseded',
                'rejected'
            )
        ),
    CONSTRAINT remediation_initiative_evidence_required
        CHECK (
            truth_status_code NOT IN ('authoritative', 'observed')
            OR evidence_record_id IS NOT NULL
        ),
    CONSTRAINT remediation_initiative_active_interval_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            initiative_code WITH =,
            tstzrange(valid_from, valid_to, '[)') WITH &&
        ) WHERE (
            superseded_at IS NULL
            AND truth_status_code = 'authoritative'
        )
);

CREATE TABLE architecture_core.initiative_objective_link (
    tenant_record_id uuid NOT NULL,
    initiative_objective_link_id uuid NOT NULL DEFAULT uuidv7(),
    remediation_initiative_id uuid NOT NULL,
    strategy_objective_id uuid NOT NULL,
    contribution_type_code text NOT NULL,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    superseded_at timestamptz,
    truth_status_code text NOT NULL,
    evidence_record_id uuid,
    CONSTRAINT initiative_objective_link_primary_key
        PRIMARY KEY (tenant_record_id, initiative_objective_link_id),
    CONSTRAINT initiative_objective_link_initiative_foreign
        FOREIGN KEY (tenant_record_id, remediation_initiative_id)
        REFERENCES architecture_core.remediation_initiative
            (tenant_record_id, remediation_initiative_id),
    CONSTRAINT initiative_objective_link_objective_foreign
        FOREIGN KEY (tenant_record_id, strategy_objective_id)
        REFERENCES architecture_core.strategy_objective
            (tenant_record_id, strategy_objective_id),
    CONSTRAINT initiative_objective_link_evidence_foreign
        FOREIGN KEY (tenant_record_id, evidence_record_id)
        REFERENCES architecture_core.evidence_record
            (tenant_record_id, evidence_record_id),
    CONSTRAINT initiative_objective_link_uuid_version
        CHECK (uuid_extract_version(initiative_objective_link_id) = 7),
    CONSTRAINT initiative_objective_link_contribution_format
        CHECK (contribution_type_code ~ '^[a-z][a-z0-9]+(?:_[a-z0-9]+)*$'),
    CONSTRAINT initiative_objective_link_valid_interval
        CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT initiative_objective_link_system_interval
        CHECK (superseded_at IS NULL OR superseded_at >= recorded_at),
    CONSTRAINT initiative_objective_link_truth_allowed
        CHECK (
            truth_status_code IN (
                'authoritative',
                'observed',
                'inferred',
                'proposed',
                'superseded',
                'rejected'
            )
        ),
    CONSTRAINT initiative_objective_link_evidence_required
        CHECK (
            truth_status_code NOT IN ('authoritative', 'observed')
            OR evidence_record_id IS NOT NULL
        ),
    CONSTRAINT initiative_objective_link_active_interval_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            remediation_initiative_id WITH =,
            strategy_objective_id WITH =,
            contribution_type_code WITH =,
            tstzrange(valid_from, valid_to, '[)') WITH &&
        ) WHERE (
            superseded_at IS NULL
            AND truth_status_code = 'authoritative'
        )
);

CREATE TABLE architecture_core.initiative_milestone (
    tenant_record_id uuid NOT NULL,
    initiative_milestone_id uuid NOT NULL DEFAULT uuidv7(),
    remediation_initiative_id uuid NOT NULL,
    milestone_code text NOT NULL,
    milestone_title text NOT NULL,
    milestone_description text,
    sequence_number integer NOT NULL,
    target_at timestamptz NOT NULL,
    valid_from timestamptz NOT NULL,
    valid_to timestamptz,
    recorded_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    superseded_at timestamptz,
    truth_status_code text NOT NULL,
    evidence_record_id uuid,
    CONSTRAINT initiative_milestone_primary_key
        PRIMARY KEY (tenant_record_id, initiative_milestone_id),
    CONSTRAINT initiative_milestone_initiative_foreign
        FOREIGN KEY (tenant_record_id, remediation_initiative_id)
        REFERENCES architecture_core.remediation_initiative
            (tenant_record_id, remediation_initiative_id),
    CONSTRAINT initiative_milestone_evidence_foreign
        FOREIGN KEY (tenant_record_id, evidence_record_id)
        REFERENCES architecture_core.evidence_record
            (tenant_record_id, evidence_record_id),
    CONSTRAINT initiative_milestone_uuid_version
        CHECK (uuid_extract_version(initiative_milestone_id) = 7),
    CONSTRAINT initiative_milestone_code_format
        CHECK (milestone_code ~ '^[a-z][a-z0-9]+(?:_[a-z0-9]+)*$'),
    CONSTRAINT initiative_milestone_title_nonempty
        CHECK (length(btrim(milestone_title)) > 0),
    CONSTRAINT initiative_milestone_description_length
        CHECK (
            milestone_description IS NULL
            OR length(milestone_description) BETWEEN 1 AND 4096
        ),
    CONSTRAINT initiative_milestone_sequence_positive
        CHECK (sequence_number > 0),
    CONSTRAINT initiative_milestone_valid_interval
        CHECK (valid_to IS NULL OR valid_to > valid_from),
    CONSTRAINT initiative_milestone_system_interval
        CHECK (superseded_at IS NULL OR superseded_at >= recorded_at),
    CONSTRAINT initiative_milestone_truth_allowed
        CHECK (
            truth_status_code IN (
                'authoritative',
                'observed',
                'inferred',
                'proposed',
                'superseded',
                'rejected'
            )
        ),
    CONSTRAINT initiative_milestone_evidence_required
        CHECK (
            truth_status_code NOT IN ('authoritative', 'observed')
            OR evidence_record_id IS NOT NULL
        ),
    CONSTRAINT initiative_milestone_active_interval_exclusion
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            remediation_initiative_id WITH =,
            milestone_code WITH =,
            tstzrange(valid_from, valid_to, '[)') WITH &&
        ) WHERE (
            superseded_at IS NULL
            AND truth_status_code = 'authoritative'
        )
);

CREATE FUNCTION architecture_core.validate_initiative_objective_link_semantics()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  initiative_valid_from timestamptz;
  initiative_valid_to timestamptz;
  objective_valid_from timestamptz;
  objective_valid_to timestamptz;
BEGIN
  SELECT valid_from, valid_to
    INTO initiative_valid_from, initiative_valid_to
    FROM architecture_core.remediation_initiative
   WHERE tenant_record_id = NEW.tenant_record_id
     AND remediation_initiative_id = NEW.remediation_initiative_id;

  SELECT valid_from, valid_to
    INTO objective_valid_from, objective_valid_to
    FROM architecture_core.strategy_objective
   WHERE tenant_record_id = NEW.tenant_record_id
     AND strategy_objective_id = NEW.strategy_objective_id;

  IF initiative_valid_from IS NOT NULL
     AND NOT (
        tstzrange(NEW.valid_from, NEW.valid_to, '[)')
        <@ tstzrange(initiative_valid_from, initiative_valid_to, '[)')
     ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'initiative-objective link validity exceeds initiative validity';
  END IF;

  IF objective_valid_from IS NOT NULL
     AND NOT (
        tstzrange(NEW.valid_from, NEW.valid_to, '[)')
        <@ tstzrange(objective_valid_from, objective_valid_to, '[)')
     ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'initiative-objective link validity exceeds objective validity';
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER initiative_objective_link_semantic_guard
BEFORE INSERT OR UPDATE OF
    tenant_record_id,
    remediation_initiative_id,
    strategy_objective_id,
    valid_from,
    valid_to
ON architecture_core.initiative_objective_link
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_initiative_objective_link_semantics();

CREATE FUNCTION architecture_core.validate_initiative_milestone_semantics()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  initiative_valid_from timestamptz;
  initiative_valid_to timestamptz;
BEGIN
  SELECT valid_from, valid_to
    INTO initiative_valid_from, initiative_valid_to
    FROM architecture_core.remediation_initiative
   WHERE tenant_record_id = NEW.tenant_record_id
     AND remediation_initiative_id = NEW.remediation_initiative_id;

  IF initiative_valid_from IS NOT NULL
     AND NOT (
        tstzrange(NEW.valid_from, NEW.valid_to, '[)')
        <@ tstzrange(initiative_valid_from, initiative_valid_to, '[)')
     ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'milestone validity exceeds initiative validity';
  END IF;

  IF initiative_valid_from IS NOT NULL
     AND NOT (
        NEW.target_at
        <@ tstzrange(initiative_valid_from, initiative_valid_to, '[)')
     ) THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'milestone target lies outside initiative validity';
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER initiative_milestone_semantic_guard
BEFORE INSERT OR UPDATE OF
    tenant_record_id,
    remediation_initiative_id,
    target_at,
    valid_from,
    valid_to
ON architecture_core.initiative_milestone
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_initiative_milestone_semantics();

CREATE FUNCTION architecture_core.reject_strategy_meaning_mutation()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  RAISE EXCEPTION USING
    ERRCODE = '23514',
    MESSAGE = 'versioned strategy meaning is immutable; supersede and append a new fact';
END;
$$;

CREATE FUNCTION architecture_core.validate_strategy_supersession()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF OLD.superseded_at IS NOT NULL
     AND NEW.superseded_at IS DISTINCT FROM OLD.superseded_at THEN
    RAISE EXCEPTION USING
      ERRCODE = '23514',
      MESSAGE = 'strategy supersession time is immutable once recorded';
  END IF;

  RETURN NEW;
END;
$$;

CREATE TRIGGER strategy_objective_immutable_guard
BEFORE UPDATE OF
    tenant_record_id,
    strategy_objective_id,
    objective_code,
    objective_title,
    objective_description,
    valid_from,
    valid_to,
    recorded_at,
    truth_status_code,
    evidence_record_id
ON architecture_core.strategy_objective
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_strategy_meaning_mutation();

CREATE TRIGGER strategy_objective_supersession_guard
BEFORE UPDATE OF superseded_at
ON architecture_core.strategy_objective
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_strategy_supersession();

CREATE TRIGGER remediation_initiative_immutable_guard
BEFORE UPDATE OF
    tenant_record_id,
    remediation_initiative_id,
    initiative_code,
    initiative_title,
    initiative_description,
    valid_from,
    valid_to,
    recorded_at,
    truth_status_code,
    evidence_record_id
ON architecture_core.remediation_initiative
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_strategy_meaning_mutation();

CREATE TRIGGER remediation_initiative_supersession_guard
BEFORE UPDATE OF superseded_at
ON architecture_core.remediation_initiative
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_strategy_supersession();

CREATE TRIGGER initiative_objective_link_immutable_guard
BEFORE UPDATE OF
    tenant_record_id,
    initiative_objective_link_id,
    remediation_initiative_id,
    strategy_objective_id,
    contribution_type_code,
    valid_from,
    valid_to,
    recorded_at,
    truth_status_code,
    evidence_record_id
ON architecture_core.initiative_objective_link
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_strategy_meaning_mutation();

CREATE TRIGGER initiative_objective_link_supersession_guard
BEFORE UPDATE OF superseded_at
ON architecture_core.initiative_objective_link
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_strategy_supersession();

CREATE TRIGGER initiative_milestone_immutable_guard
BEFORE UPDATE OF
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
    recorded_at,
    truth_status_code,
    evidence_record_id
ON architecture_core.initiative_milestone
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_strategy_meaning_mutation();

CREATE TRIGGER initiative_milestone_supersession_guard
BEFORE UPDATE OF superseded_at
ON architecture_core.initiative_milestone
FOR EACH ROW
EXECUTE FUNCTION architecture_core.validate_strategy_supersession();

ALTER TABLE architecture_core.strategy_objective ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.strategy_objective FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.strategy_objective
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.remediation_initiative ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.remediation_initiative FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.remediation_initiative
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.initiative_objective_link ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.initiative_objective_link FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.initiative_objective_link
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

ALTER TABLE architecture_core.initiative_milestone ENABLE ROW LEVEL SECURITY;
ALTER TABLE architecture_core.initiative_milestone FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_policy ON architecture_core.initiative_milestone
    USING (tenant_record_id = architecture_core.current_tenant_id())
    WITH CHECK (tenant_record_id = architecture_core.current_tenant_id());

COMMIT;
