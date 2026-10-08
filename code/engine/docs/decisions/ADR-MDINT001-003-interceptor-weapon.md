# ADR-MDINT001-003: Interceptor weapon compatibility

Status: Accepted

## Context

MD-INT-001 uses configured UAV interceptor and shore CIWS resources.  Weapon behavior
must remain a resource/target-domain decision rather than a fixed-entity special case.

## Options

- Put weapon rules in the scenario controller.
- Declare compatible weapon, platform, guidance and target-domain resources.

## Decision

Use the versioned weapon configuration: the UAV interceptor and shore CIWS are air-target
resources, resolved and validated before the authority combat chain executes.

## Consequences

Illegal combinations fail through compatibility/ROE checks without ammunition or RNG side
effects.  Range, probability and damage values retain their declared benchmark provenance.

## Configuration

`weapons` in `md_int_001_v1.yaml` and `WeaponConfig` are the compatibility source.

