# ADR-MDINT001-005: Breach priority

Status: Accepted

## Context

The interception benchmark needs an unambiguous terminal result when a protected-area
breach and other same-tick outcomes occur together.

## Options

- Let entity iteration order determine the result.
- Evaluate the configured mission conditions in a stable priority order and latch the winner.

## Decision

Use the common mission/adjudication path with breach-first terminal priority and a latched
authority receipt.  Re-evaluation after terminal state returns the same result.

## Consequences

Same-tick results are reproducible and explainable in logs/checkpoints.  Priority is a
benchmark rule, not a general claim about real-world doctrine.

## Configuration

`adjudication` in `md_int_001_v1.yaml` defines the benchmark mission selection.

