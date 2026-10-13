\set ON_ERROR_STOP on

DO $$
DECLARE
    expected_tables text[] := ARRAY[
        'evidence_record',
        'outbox_event',
        'projection_receipt',
        'transformation_history_record'
    ];
    table_name text;
    table_options text[];
BEGIN
    IF to_regprocedure(
        'architecture_core.hot_partition_bucket(uuid)'
    ) IS NULL THEN
        RAISE EXCEPTION 'hot partition routing function is missing';
    END IF;

    IF architecture_core.hot_partition_bucket(
        '0195d145-64e8-7f4f-8a23-a0cc784c1234'
    ) NOT BETWEEN 0 AND 15 THEN
        RAISE EXCEPTION 'hot partition bucket is outside the configured range';
    END IF;

    IF architecture_core.hot_partition_bucket(
        '0195d145-64e8-7f4f-8a23-a0cc784c1234'
    ) IS DISTINCT FROM architecture_core.hot_partition_bucket(
        '0195d145-64e8-7f4f-8a23-a0cc784c1234'
    ) THEN
        RAISE EXCEPTION 'hot partition bucket is not deterministic';
    END IF;

    FOREACH table_name IN ARRAY expected_tables LOOP
        SELECT reloptions
          INTO table_options
          FROM pg_class
         WHERE oid = format('architecture_core.%s', table_name)::regclass;
        IF table_options IS NULL
           OR NOT ('fillfactor=80' = ANY(table_options)) THEN
            RAISE EXCEPTION 'fillfactor is not prepared for %', table_name;
        END IF;
    END LOOP;

    IF to_regclass('architecture_core.evidence_record_hot_write_index') IS NULL
       OR to_regclass('architecture_core.outbox_event_hot_write_index') IS NULL
       OR to_regclass('architecture_core.projection_receipt_hot_write_index') IS NULL
       OR to_regclass(
           'architecture_core.transformation_history_hot_write_index'
       ) IS NULL THEN
        RAISE EXCEPTION 'one or more hot-write indexes are missing';
    END IF;
END;
$$;

SELECT 'hot-write-capacity-ok' AS verification;
