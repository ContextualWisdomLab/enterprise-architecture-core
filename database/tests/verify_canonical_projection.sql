\set ON_ERROR_STOP on

-- Regression for the normalized canonical-reference contract: canonical asset URIs
-- are derived from authoritative identity determinants rather than persisted.
INSERT INTO architecture_core.tenant_record (
    tenant_record_id,
    tenant_code,
    tenant_title
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb713',
    'projection_test',
    'Canonical Projection Test'
);

INSERT INTO architecture_core.architecture_object (
    tenant_record_id,
    architecture_object_id,
    object_type_id
) VALUES (
    '0195d145-64e8-7f4f-8a23-a0cc784cb713',
    '0195d145-64e8-7f4f-8a23-a0cc784cb906',
    '0195d145-64e8-7f4f-8a23-a0cc784cb802'
);

DO $$
DECLARE
  projected_asset_uri text;
BEGIN
  SELECT canonical_asset_uri
    INTO projected_asset_uri
    FROM architecture_core.architecture_object_reference
   WHERE tenant_record_id = '0195d145-64e8-7f4f-8a23-a0cc784cb713'
     AND architecture_object_id = '0195d145-64e8-7f4f-8a23-a0cc784cb906';

  IF projected_asset_uri IS DISTINCT FROM
      'urn:cwl:projection_test:ea_core:application_record:0195d145-64e8-7f4f-8a23-a0cc784cb906' THEN
    RAISE EXCEPTION
      'canonical asset projection mismatch: %',
      projected_asset_uri;
  END IF;
END;
$$;
