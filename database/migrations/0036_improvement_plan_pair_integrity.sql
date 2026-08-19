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

COMMIT;
