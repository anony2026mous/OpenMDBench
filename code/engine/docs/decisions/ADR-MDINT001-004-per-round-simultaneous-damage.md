# ADR-MDINT001-004: Per-round simultaneous damage

Status: Accepted

## Context

Entity traversal order must not decide the result when several effects occur in one fixed
tick.

## Options

- Apply each hit immediately in attacker iteration order.
- Collect authority damage intents and resolve them in stable simultaneous order.

## Decision

Weapon, collision and other accepted effects create evidence-backed damage intents.  The
common damage path aggregates and resolves the intents once for the tick.

## Consequences

Outcome is deterministic under registration-order changes and each health/lifecycle change
has an auditable source.  It does not assert any particular real-world lethality model.

## Configuration

The configured damage component supplies the selected benchmark response profile.

