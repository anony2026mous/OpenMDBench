# ADR-MDINT001-001: Weihai world and time

Status: Accepted

## Context

MD-INT-001 needs a reproducible map identity, coordinate basis and simulation clock.  The
frozen configuration identifies `weihai_v1@1.0`, its WGS84/legacy asset hashes, and a
one-second fixed tick with a 900-tick benchmark limit.

## Options

- Infer the map or clock from the host environment.
- Freeze map identity and clock in the versioned configuration.

## Decision

Use the configured Weihai asset identity, EPSG:4326 source coordinates and the existing
local-coordinate conversion path.  Advance the authority world at one fixed second per
tick; wall-clock speed never changes logical time.

## Consequences

Logs, checkpoints and replay can validate a stable map/time anchor.  The selected harbour
entry is a benchmark scenario input, not a claim of real-world operational fidelity.

## Configuration

`openmdbench/config/md_int_001_v1.yaml` and
`openmdbench/scenarios/md_int_001_config.py` are the normative frozen configuration.

