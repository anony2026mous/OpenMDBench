# ADR-MDINT001-002: UAV kinematics

Status: Accepted

## Context

The benchmark requires UAV movement that is deterministic, bounded and compatible with
the common fixed-tick world, without presenting an unvalidated aircraft model as a
calibrated flight-dynamics model.

## Options

- Use host- or scenario-specific movement code.
- Use the existing versioned UAV kinematic component through the common dynamics path.

## Decision

Use the existing deterministic UAV kinematic adapter and its configuration-defined limits.
Navigation is expressed in the common coordinate and heading conventions and commits only
through the authority tick.

## Consequences

The UAV remains compatible with observation, boundary, energy, checkpoint and replay
paths.  Benchmark parameter provenance remains explicit and is not real-aircraft
calibration.

## Configuration

The `dynamics.uav` and `energy.uav` entries in `md_int_001_v1.yaml` select the profile.

