BEGIN;

-- Promote the existing 0005 grammar guard to the cross-domain contract name
-- instead of evaluating an identical check twice on every receipt write.
ALTER TABLE architecture_core.projection_receipt
    RENAME CONSTRAINT projection_receipt_source_format
    TO projection_receipt_source_uri_format;

COMMIT;
