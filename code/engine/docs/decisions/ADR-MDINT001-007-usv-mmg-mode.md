# ADR-MDINT001-007: USV MMG mode

Status: Accepted

## Context

The surface craft needs an adapter to the repository's Sim2Sea MMG solver while preserving
session isolation, common navigation semantics and reproducible checkpoint behavior.

## Options

- Expose raw solver controls directly to a scenario.
- Use the existing session-owned MMG adapter behind the common dynamics boundary.

## Decision

Use the Sim2Sea MMG adapter with bounded propulsion and rudder commands derived from the
common navigation command.  The `kvlcc2_l7` parameter identity is retained as an abstract
benchmark wiring profile only.

## Consequences

The solver state is session-local and restorable.  This does not claim that the profile
calibrates an operational USV.

## Configuration

`dynamics.usv` in `md_int_001_v1.yaml` selects the versioned MMG profile.

