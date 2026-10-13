# User Stories

These stories describe the next action a buyer or operator should take with the
current foundation. They are not a backlog of unimplemented UI work.

## Confirm the process is alive

As an operator preparing a deployment, I start the `ea-core` process and call
`GET /health`. When the payload names `enterprise-architecture-core` and
`alive`, I next call `GET /ready` before adding the instance to a load
balancer.

## Keep an unready instance out of traffic

As an operator, I treat HTTP 503 from `GET /ready` as a signal to inspect
`contract_ready` and `database_ready`, repair that dependency, and retry the
probe. I do not send tenant commands to a 503 instance.

## Connect Keyverse before domain commands

As a security reviewer, I set `EA_OIDC_ISSUER`, `EA_OIDC_AUDIENCE`, and
`EA_OIDC_JWKS_URL` to the Keyverse deployment. I do not store passwords or
email addresses in this database.

## Link Data/AI context without copying it

As an enterprise architect, I reference Semantic Data Portal objects by
canonical asset URI. I keep glossary, lineage, and certification facts in
Semantic Data Portal.

## Review inferred and observed evidence

As a transformation lead, I accept LineageWeave proposals and pg-erd-cloud
observed-schema evidence only after an explicit reviewed command. I do not
treat those inputs as current-state truth on arrival.
