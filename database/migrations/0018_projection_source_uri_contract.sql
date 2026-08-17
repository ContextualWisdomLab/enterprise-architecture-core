BEGIN;

ALTER TABLE architecture_core.projection_receipt
    ADD CONSTRAINT projection_receipt_source_uri_format
    CHECK (
        event_source_uri ~
        '^urn:cwl:(?=[^:]{2,63}:)[a-z][a-z0-9]+(?:_[a-z0-9]+)*:(?=[^:]{2,63}$)[a-z][a-z0-9]+(?:_[a-z0-9]+)*$'
    );

COMMIT;
