# Enterprise Architecture Core

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/ContextualWisdomLab/enterprise-architecture-core)

**The authoritative enterprise architecture and transformation decision plane for the ContextualWisdomLab ecosystem.**

Enterprise Architecture Core records how bounded contexts relate, where authority lives, and which transformation decisions apply across products. It provides durable context maps and decision evidence without taking domain truth, runtime control, or deployment ownership away from product repositories.

## Responsibility

- Maintain the enterprise Context Map and cross-context relationship decisions.
- Record architecture and transformation decisions with constraints, alternatives, evidence, risks, effects, and follow-up.
- Make ownership, upstream/downstream dependency, and anti-corruption boundaries visible to product teams and operators.
- Preserve decision history so a new contributor can reconstruct why the current architecture exists.

## Boundary

Product repositories retain their Ubiquitous Language, domain rules, aggregates, data ownership, and release authority. Shared services and libraries are optional integrations behind versioned contracts; this repository does not turn an architectural decision into mandatory runtime infrastructure.

Open proposals remain proposals until their evidence, review, and protected-branch integration are complete.

## Current status

This repository is a documentation and decision-authority source under active development. No executable package or release is currently published. There is no install command or hosted application to operate.

To evaluate the current proposal:

1. Read the [public overview](docs/index.md).
2. Review the [Product and technical gap baseline](docs/product-technical-gap-baseline.md).
3. Treat pull-request content as Proposed until it is reviewed and integrated into the protected branch.

## Integration

Product contexts consume accepted enterprise decisions and released contracts through explicit anti-corruption layers. They do not depend on this repository at runtime, copy its source, or surrender ownership of their Ubiquitous Language, aggregates, APIs, data, operations, or releases.

## Documentation

The concise buyer- and operator-facing overview is maintained in [docs/index.md](docs/index.md). Protected default-branch content remains authoritative.

## Support

Use [GitHub Issues](https://github.com/ContextualWisdomLab/enterprise-architecture-core/issues) for reproducible documentation, ownership, or decision-evidence gaps. Do not include secrets, credentials, customer data, or private operational details.

## License

No repository-level `LICENSE` is present. Public visibility is not a grant of reuse rights. A license, provenance review, third-party attribution, and any required NOTICE must be established before a distributable release is represented as reusable.
