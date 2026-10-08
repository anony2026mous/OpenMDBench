# ADR-001: Scenario identity and hash

Status: Accepted

## Context

Formal scenarios must remain distinguishable when names, files and execution environments vary.

## Decision

Use explicit scenario identifiers and a deterministic resolved configuration hash. Runtime consumes
the resolved artifact rather than inferring a scenario from mutable source files.

## Consequences

Logs, checkpoints and replay bind to a stable identity. This is a benchmark reproducibility rule,
not a claim about operational data provenance.
