\set ON_ERROR_STOP on

DO $$
DECLARE
  runtime_superuser boolean;
  runtime_bypasses_rls boolean;
  runtime_owns_table boolean;
BEGIN
  IF current_user <> 'ea_runtime' THEN
    RAISE EXCEPTION 'runtime acceptance must execute as ea_runtime, got %', current_user;
  END IF;

  SELECT rolsuper, rolbypassrls
    INTO runtime_superuser, runtime_bypasses_rls
    FROM pg_catalog.pg_roles
   WHERE rolname = current_user;

  IF runtime_superuser OR runtime_bypasses_rls THEN
    RAISE EXCEPTION
      'runtime role must be non-superuser and must not bypass row-level security';
  END IF;

  SELECT EXISTS (
      SELECT 1
        FROM pg_catalog.pg_class AS table_record
        JOIN pg_catalog.pg_namespace AS namespace_record
          ON namespace_record.oid = table_record.relnamespace
       WHERE namespace_record.nspname = 'architecture_core'
         AND table_record.relkind IN ('r', 'p')
         AND pg_get_userbyid(table_record.relowner) = current_user
  ) INTO runtime_owns_table;

  IF runtime_owns_table THEN
    RAISE EXCEPTION 'runtime role must not own architecture_core tables';
  END IF;
END;
$$;

SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

DO $$
DECLARE
  visible_tenant_count integer;
BEGIN
  SELECT count(*)
    INTO visible_tenant_count
    FROM architecture_core.tenant_record;

  IF visible_tenant_count <> 1 THEN
    RAISE EXCEPTION
      'runtime row-level security exposed % tenant rows',
      visible_tenant_count;
  END IF;
END;
$$;

INSERT INTO architecture_core.evidence_record (
    tenant_record_id,
    evidence_record_id,
    evidence_uri,
    sha256_digest
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    '0195d145-64e8-7f4f-8a23-a0cc784cbe01',
    'urn:cwl:evidence:runtime_allowed',
    repeat('a', 64)
);

DO $$
BEGIN
  BEGIN
    INSERT INTO architecture_core.evidence_record (
        tenant_record_id,
        evidence_record_id,
        evidence_uri,
        sha256_digest
    ) VALUES (
        '0195d145-64e8-7f4f-8a23-a0cc784cb712',
        '0195d145-64e8-7f4f-8a23-a0cc784cbe02',
        'urn:cwl:evidence:runtime_denied',
        repeat('b', 64)
    );
    RAISE EXCEPTION 'cross-tenant runtime insert unexpectedly succeeded';
  EXCEPTION
    WHEN insufficient_privilege THEN NULL;
  END;
END;
$$;
