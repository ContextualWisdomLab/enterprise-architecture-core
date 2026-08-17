\set ON_ERROR_STOP on

-- Buyer acceptance for versioned strategy execution. This test intentionally
-- lands before migration 0011 so the first hosted run is RED at the missing
-- authoritative tables rather than at an implementation detail.

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

-- The implemented migration must preserve tenant ownership, bitemporal
-- meaning, explicit truth origin, evidence requirements, immutable semantic
-- history, initiative/objective consistency, and executable milestone order.
-- Concrete fixtures and negative cases are added in the GREEN implementation
-- commit once the missing-table RED boundary has been observed in hosted CI.
