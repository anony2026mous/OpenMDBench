"""Create immutable-source and endpoint inventory for the P1 six-arm campaign."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import p0_6_audit
import p0_6_smoke


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()
    output = args.output_dir
    if output.exists() and any(output.iterdir()):
        raise FileExistsError(f"P1 campaign directory must be empty: {output}")
    output.mkdir(parents=True, exist_ok=True)
    provenance = p0_6_audit.freeze(output)
    inventory = p0_6_audit.inventory(output)
    if inventory["confirmatory_seed_201_203_count"]:
        raise RuntimeError("Selected 201–203 seeds already appear in candidate history")
    paths = (
        p0_6_audit.EVAL / "_gen_ie_set_ext.py",
        p0_6_audit.ENGINE / "openmdbench" / "world" / "factory_v2.py",
    )
    provenance["extra_files_sha256"] = {
        str(path.relative_to(p0_6_audit.PROJECT)).replace("\\", "/"):
        p0_6_audit.sha256(path) for path in paths
    }
    p0_6_audit.save(output / "provenance.json", provenance)
    p0_6_smoke.probe(output)
    print(json.dumps({
        "output": str(output), "scenarios": {
            key: value["resolved_hash"] for key, value in provenance["scenarios"].items()
        }, "selected_seed_overlap": inventory["confirmatory_seed_201_203_count"],
        "endpoint_model_present": True,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
