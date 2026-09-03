BEGIN;

-- Keep EA projection receipts compatible with the CGC structured CloudEvent
-- admission surface. HTTP optional whitespace is SP / HTAB only; CR/LF, VT and
-- FF remain invalid so transport metadata cannot smuggle line-oriented syntax.
ALTER TABLE architecture_core.context_assertion_projection_receipt
    DROP CONSTRAINT context_assertion_projection_receipt_media_type;

ALTER TABLE architecture_core.context_assertion_projection_receipt
    ADD CONSTRAINT context_assertion_projection_receipt_media_type
        CHECK (
            transport_media_type ~*
            E'\\A[ \t]*application/cloudevents[+]json[ \t]*(;[ \t]*charset[ \t]*=[ \t]*("utf-8"|utf-8)[ \t]*)?\\Z'
        );

COMMENT ON CONSTRAINT context_assertion_projection_receipt_media_type
ON architecture_core.context_assertion_projection_receipt IS
'Admits the CGC structured JSON CloudEvent media type, optional UTF-8 charset, and HTTP SP/HTAB OWS while rejecting other control characters.';

COMMIT;
