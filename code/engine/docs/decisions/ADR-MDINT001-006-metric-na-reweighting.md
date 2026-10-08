# ADR-MDINT001-006: Metric N/A reweighting

Status: Accepted

## Context

Some scoring metrics are structurally inapplicable to a completed benchmark run, while a
missing value for an applicable metric is a data-quality defect.

## Options

- Treat all absent metrics as zero.
- Distinguish structural N/A from missing required evidence and normalize only N/A weights.

## Decision

Represent structural N/A as an explicit null value and reweight the applicable metrics.
Required-but-missing evidence scores zero and is recorded as a metric-data defect.

## Consequences

Scores remain comparable without hiding instrumentation failures.  Metric weights remain
benchmark configuration rather than externally validated performance claims.

## Configuration

`scoring` in `md_int_001_v1.yaml` declares the selected metric profile.

