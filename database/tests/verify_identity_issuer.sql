\set ON_ERROR_STOP on

SELECT set_config(
    'app.tenant_record_id',
    '0195d145-64e8-7f4f-8a23-a0cc784cb711',
    false
);

INSERT INTO architecture_core.identity_link (
    tenant_record_id,
    issuer_uri,
    keyverse_subject_id,
    valid_from,
    valid_to
) VALUES
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        'https://keyverse.example/issuer-a',
        'same_subject',
        '2026-01-01T00:00:00Z',
        '2026-07-01T00:00:00Z'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb711',
        'https://keyverse.example/issuer-b',
        'same_subject',
        '2026-01-01T00:00:00Z',
        '2026-07-01T00:00:00Z'
    );

DO $$
BEGIN
    BEGIN
        INSERT INTO architecture_core.identity_link (
            tenant_record_id,
            issuer_uri,
            keyverse_subject_id,
            valid_from
        ) VALUES (
            '0195d145-64e8-7f4f-8a23-a0cc784cb711',
            'https://keyverse.example/issuer-a',
            'same_subject',
            '2026-06-01T00:00:00Z'
        );
        RAISE EXCEPTION 'overlapping issuer-subject link was accepted';
    EXCEPTION
        WHEN exclusion_violation THEN NULL;
    END;
END;
$$;

DO $$
BEGIN
    BEGIN
        UPDATE architecture_core.identity_link
           SET issuer_uri = 'https://keyverse.example/issuer-c'
         WHERE issuer_uri = 'https://keyverse.example/issuer-a'
           AND keyverse_subject_id = 'same_subject';
        RAISE EXCEPTION 'identity link key mutation was accepted';
    EXCEPTION
        WHEN check_violation THEN NULL;
    END;
END;
$$;

RESET app.tenant_record_id;
