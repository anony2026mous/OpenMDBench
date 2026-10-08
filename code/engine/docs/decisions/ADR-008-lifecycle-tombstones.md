# ADR-008: Lifecycle tombstones

Status: Accepted

## Context

Destroyed or breached entities can remain relevant to collision, audit and mission history.

## Decision

Represent lifecycle transitions explicitly and retain only the policy-selected tombstone/wreck
state required for authoritative continuation and replay.

## Consequences

Disabled entities are not treated as operational, while their recorded lifecycle evidence remains
available to authorized replay and checkpoint consumers.
