# ADR-009: Weather profiles

Status: Accepted

## Context

Difficulty-specific weather effects must begin and end at stable logical ticks.

## Decision

Represent weather as declared, versioned scenario profiles evaluated by the common tick pipeline.

## Consequences

The same seed and timeline produce the same weather modifiers and checkpoint continuation. Values
are benchmark inputs, not meteorological validation claims.
