BEGIN;

INSERT INTO architecture_core.object_type (
    object_type_id,
    object_type_code,
    object_type_title
) VALUES
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb801',
        'business_capability',
        'Business Capability'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb802',
        'application_record',
        'Application'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb803',
        'technology_component',
        'Technology Component'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb804',
        'organization_unit',
        'Organization Unit'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb805',
        'application_interface',
        'Application Interface'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb806',
        'technology_provider',
        'Technology Provider'
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb807',
        'technology_version',
        'Technology Version'
    );

INSERT INTO architecture_core.lifecycle_phase (
    lifecycle_phase_id,
    lifecycle_phase_code,
    display_order
) VALUES
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb823',
        'planned',
        1
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb821',
        'active',
        2
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb822',
        'phase_out',
        3
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb824',
        'end_of_life',
        4
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb825',
        'retired',
        5
    );

INSERT INTO architecture_core.relation_type (
    relation_type_id,
    relation_type_code,
    source_type_id,
    target_type_id,
    forward_only_flag
) VALUES
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb811',
        'supports_capability',
        '0195d145-64e8-7f4f-8a23-a0cc784cb802',
        '0195d145-64e8-7f4f-8a23-a0cc784cb801',
        true
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb812',
        'uses_technology',
        '0195d145-64e8-7f4f-8a23-a0cc784cb802',
        '0195d145-64e8-7f4f-8a23-a0cc784cb803',
        true
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb813',
        'exposes_interface',
        '0195d145-64e8-7f4f-8a23-a0cc784cb802',
        '0195d145-64e8-7f4f-8a23-a0cc784cb805',
        true
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb814',
        'consumes_interface',
        '0195d145-64e8-7f4f-8a23-a0cc784cb802',
        '0195d145-64e8-7f4f-8a23-a0cc784cb805',
        true
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb815',
        'provided_by',
        '0195d145-64e8-7f4f-8a23-a0cc784cb803',
        '0195d145-64e8-7f4f-8a23-a0cc784cb806',
        true
    ),
    (
        '0195d145-64e8-7f4f-8a23-a0cc784cb816',
        'has_version',
        '0195d145-64e8-7f4f-8a23-a0cc784cb803',
        '0195d145-64e8-7f4f-8a23-a0cc784cb807',
        true
    );

COMMIT;
