\set ON_ERROR_STOP on

-- A governed replan must not create an unbounded replacement inside bounded
-- scenario and initiative authority. The replacement inherits the narrowest
-- enclosing business-validity upper bound so later state changes cannot escape
-- the approved target-state context.

SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
DECLARE
  replacement_valid_to timestamptz;
  scenario_valid_to timestamptz;
  initiative_valid_to timestamptz;
BEGIN
  SELECT transformation_record.valid_to
    INTO replacement_valid_to
    FROM architecture_core.architecture_transformation AS transformation_record
   WHERE transformation_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND transformation_record.architecture_transformation_id =
         '0196e250-1111-7111-8111-111111111191';

  SELECT scenario_record.valid_to
    INTO scenario_valid_to
    FROM architecture_core.architecture_scenario AS scenario_record
   WHERE scenario_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND scenario_record.architecture_scenario_id =
         '0196e002-1111-7111-8111-111111111111';

  SELECT initiative_record.valid_to
    INTO initiative_valid_to
    FROM architecture_core.remediation_initiative AS initiative_record
   WHERE initiative_record.tenant_record_id =
         '0195d145-64e8-7f4f-8a23-a0cc784cb711'
     AND initiative_record.remediation_initiative_id =
         '0196e001-1111-7111-8111-111111111111';

  IF replacement_valid_to IS DISTINCT FROM
       LEAST(scenario_valid_to, initiative_valid_to) THEN
    RAISE EXCEPTION
      'replacement validity % did not inherit enclosing bound %',
      replacement_valid_to,
      LEAST(scenario_valid_to, initiative_valid_to);
  END IF;
END;
$$;
