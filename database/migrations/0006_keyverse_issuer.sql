BEGIN;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM architecture_core.identity_link) THEN
        RAISE EXCEPTION
            'identity_link must be empty before adding issuer-qualified identity';
    END IF;
END;
$$;

ALTER TABLE architecture_core.identity_link
    DROP CONSTRAINT identity_link_subject_unique,
    DROP CONSTRAINT identity_link_active_interval_exclusion,
    ADD COLUMN issuer_uri text NOT NULL,
    ADD CONSTRAINT identity_link_issuer_nonempty
        CHECK (length(btrim(issuer_uri)) > 0),
    ADD CONSTRAINT identity_link_issuer_format
        CHECK (
            issuer_uri ~
            '^https://[^[:space:]?#]+(?:/[^[:space:]?#]*)?$'
        ),
    ADD CONSTRAINT identity_link_issuer_subject_unique
        UNIQUE (
            tenant_record_id,
            issuer_uri,
            keyverse_subject_id,
            valid_from
        ),
    ADD CONSTRAINT identity_link_issuer_subject_validity_exclude
        EXCLUDE USING gist (
            tenant_record_id WITH =,
            issuer_uri WITH =,
            keyverse_subject_id WITH =,
            tstzrange(valid_from, valid_to, '[)') WITH &&
        ) WHERE (superseded_at IS NULL);

CREATE FUNCTION architecture_core.reject_identity_key_change()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, architecture_core
AS $$
BEGIN
    IF NEW.tenant_record_id IS DISTINCT FROM OLD.tenant_record_id
       OR NEW.issuer_uri IS DISTINCT FROM OLD.issuer_uri
       OR NEW.keyverse_subject_id IS DISTINCT FROM OLD.keyverse_subject_id
       OR NEW.valid_from IS DISTINCT FROM OLD.valid_from THEN
        RAISE EXCEPTION 'identity link key is immutable'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER preserve_identity_link_key
BEFORE UPDATE OF
    tenant_record_id,
    issuer_uri,
    keyverse_subject_id,
    valid_from
ON architecture_core.identity_link
FOR EACH ROW
EXECUTE FUNCTION architecture_core.reject_identity_key_change();

COMMIT;
