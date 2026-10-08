# Code comparison — local tree vs the co-author's snapshot

Answering a specific question: how far apart are the two working copies that produced the
project's results, and does the difference threaten reproducibility?

Regenerate with `python reproduce/compare_code.py`; the recorded run is
`reproduce/CODE_COMPARISON.txt`.

## Two traps a naive comparison falls into

Both are handled by the script, and both produced wrong intermediate answers first:

1. **The layouts differ.** Ours nests the harness under `code/analysis/` and the platform
   under `code/engine/`; theirs ships a flat `code/` with `eval/`, `evaluation/` and
   `scripts/`. Matching on relative path finds essentially **no** overlap, which looks
   like "the trees are unrelated" and is false.
2. **Same filename ≠ same file.** `metrics.py` exists in both trees but is a *different
   module* — theirs is the tournament/Elo evaluation harness (12.6 KB), ours is the
   strategy scorecard (5.0 KB). Compared by name they score similarity 0.01, which looks
   like total divergence and is meaningless. `validate.py` and `__init__.py` collide the
   same way.

Matched by filename, with the known collisions set aside:

## Result

| Class | Files |
|---|---|
| **Identical** (byte-for-byte) | **39** |
| **Differ only in paths / plumbing** | **190** |
| Differ, moderate edits | 1 |
| Differ, substantial | 1 |
| Same name, different module (not comparable) | 3 |
| Shared filenames total | 234 |

Our tree holds 663 distinct `.py` names against their 261; 234 overlap.

### The 190 "plumbing only" files

Measured line similarity is **1.00 with 0 changed lines** for most of them — the files are
identical except for lines matching path or environment markers (`C:\Code`,
`C:\Users`, `os.environ`, `Path(__file__)`, `_ROOT`, `_HERE`). This is the expected
consequence of moving the analysis from one machine's absolute paths to repository-relative
resolution, which was done deliberately so the release runs from any checkout.

**Interpretation: no behavioural difference.** The analysis scripts agree.

### `_w1_common.py` — moderate (similarity 0.93, 41 lines)

The one analysis file with real edits, and they are the path-resolution change described
in `REPRODUCE.md`: `RUNS`, `SNAP` and `FORMAL` now resolve relative to the repository with
an env-var fallback, instead of hard-coding one machine's layout. Verified not to change
any reported number: the main table still reproduces 70/70, and the baselines
(rule-rule 0.723, RL 0.632) are unchanged.

### `llm_client_hifi.py` — substantial (similarity 0.89, 60 lines, 245 → 297)

**This is the only difference that can affect results, and it is worth stating plainly.**
Our version adds:

| Addition | Effect |
|---|---|
| `backend` selection (`vllm` / `deepseek`), from argument or `OPENMDBENCH_LLM_BACKEND` | picks base URL, API-key variable and default model per backend |
| Backend-specific *thinking* switch | vLLM uses `chat_template_kwargs.enable_thinking`; DeepSeek needs `thinking={"type":"disabled"}`, because its `chat_template_kwargs` is **silently ignored** (HTTP 200, but the model still reasons and content comes back empty) |
| **Network retry** on `SSLError` / `ConnectionError` / `Timeout` / `ChunkedEncodingError` | an episode survives a transient disconnect (observed: one `SSLEOFError` at tick 1200 discarded a 30-minute episode); API semantic errors still fail fast |

The retry behaviour is the part that matters for reproducing an episode: a run that
survives a dropped connection on our client would have been recorded as an error on
theirs. In this release the shipped `code/analysis/llm_client_hifi.py` is **ours**.

Their original is preserved for reference at
`code/collaborator_snapshot/llm_client_hifi.py`, so anything produced under their client
can still be traced to the code that made its calls.

## What this means for the release

* **The analysis layer is agreed.** 39 files byte-identical; 190 identical but for paths.
  There is no fork in the analysis logic.
* **The platform is ours.** Their snapshot carries no `openmdbench/` at all
  (`code/engine/openmdbench/`, 432 `.py` files); `code/collaborator_snapshot/` holds only
  their evaluation tooling and the harness. See §"Layout differs" above.
* **One caveat to carry forward.** Episodes produced under their LLM client were run
  without the network retry, so their error rate is not directly comparable to ours. This
  belongs in any write-up that pools runs from both machines.
