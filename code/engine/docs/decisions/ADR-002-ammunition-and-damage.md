# ADR-002: Ammunition and damage accounting

Status: Accepted

## Context

Weapon inventories and damage results must be reproducible and auditable.

## Decision

Use the frozen scenario/Catalog ammunition inventory and declared damage model; validate legal
fire before consuming inventory and record the resulting damage evidence.

## Consequences

Rejected actions do not consume ammunition. Values remain benchmark assumptions unless separately
validated by an approved data source.
