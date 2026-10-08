# T5 resource-stability qualification

This document freezes the automated thresholds before the formal run. A smoke or short run
cannot be relabelled as a formal soak.

## Formal workload

- minimum wall duration: 2 hours for the mixed V2/GS workload;
- all four checked-in GS packages compile and pass Resolved integrity before timing;
- session churn uses fresh seeds and identities and performs authoritative World ticks;
- a bounded slow-consumer frame bus must record drops rather than block simulation;
- 100 complete Legacy MD-AD-002 matches run separately;
- 16/32 concurrent Legacy sessions run separately.

## Pass thresholds

- command exits successfully, with no deadlock, cleanup error or cross-session identity reuse;
- peak process-tree RSS is at most 4 GiB;
- after the 10% warm-up/cool-down exclusion, RSS regression slope is at most 64 MiB/hour;
- FD, thread and child-process counts return to or below the pre-run baseline;
- every owned queue remains at or below its declared capacity and is empty after close;
- retained renderer entity caches are bounded and empty after close;
- normal lockstep RTF is at least 1.0;
- the 10x/unbounded runner contract remains covered by deterministic integration tests;
- frame drops are permitted only on a bounded drop-oldest bus and must be counted.

The report records raw samples and thresholds. Missing counters or a failed gate make the
qualification fail closed.
