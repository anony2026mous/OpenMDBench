# ADR-010: Communication delivery order

Status: Accepted

## Context

Observations must not receive a message before its configured simulation-time delivery point.

## Decision

Queue valid communication records and make them visible no earlier than the next declared logical
tick according to the deterministic route and disruption rules.

## Consequences

Jamming and recovery affect visibility through the common communication model; no consumer can
observe future reports or bypass faction authorization.
