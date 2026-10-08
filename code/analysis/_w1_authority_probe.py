"""Why does the combat authority stage deny every engagement?

Under the S3/S4 strict-controller-scope contract an engagement request is
rejected with ``combat.authority_denied`` unless BOTH hold:

    evidence.controller_authorized and
    evidence.authority_token_owner_id == evidence.attacker_id

``controller_authorized`` in turn needs a single-claim entity whose claim
``controller_id`` equals the ``controller_id`` carried by the authority grant
for the token the caller passed.  This probe prints those three values side by
side per entity so a mismatch is visible directly instead of via a rejection
code.

Usage:
    python _w1_authority_probe.py [PUBLIC_ID] [--ticks N] [--seed 7]
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
sys.path.insert(0, str(ROOT))

from openmdbench.sessions.formal_v2 import create_formal_session_v2  # noqa: E402


def _ownership(session):
    view = session.world_view
    for holder in (view, getattr(session, "world", None), getattr(view, "_world", None)):
        ownership = getattr(holder, "controller_ownership", None)
        if ownership is not None:
            return ownership
    return None


def _claims(ownership, entity_id):
    for name in ("by_entity", "_by_entity"):
        method = getattr(ownership, name, None)
        if callable(method):
            try:
                return tuple(method(entity_id))
            except (KeyError, ValueError):
                return ()
    mapping = getattr(ownership, "entity_to_claims", {}) or {}
    return tuple(mapping.get(entity_id, ()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("public_id", nargs="?", default="IE-08-ISLAND-STRIKE")
    parser.add_argument("--ticks", type=int, default=6)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    session = create_formal_session_v2(args.public_id, session_id="audit.authority",
                                       seed=args.seed)
    session.load().start()
    for _ in range(args.ticks):
        session.step(operation_id=f"audit.authority.{session.world_view.tick:08d}",
                     expected_tick=session.world_view.tick)

    view = session.world_view
    tokens = dict(view.authority_tokens)
    by_entity = {grant.entity_id: token for token, grant in tokens.items()}
    ownership = _ownership(session)
    print(f"tick={view.tick} tokens={len(tokens)} ownership={'yes' if ownership else 'NO'}")
    print(f"controller_ids={tuple(getattr(ownership, 'controller_ids', ()))}")
    print()

    header = f"{'entity':<28}{'token?':<7}{'grant.ctrl':<34}{'#claim':<7}{'claim ctrl':<34}ok"
    print(header)
    print("-" * len(header))
    failures = []
    for entity in sorted(view.entities_stable(), key=lambda item: item.id):
        entity_id = entity.id
        token = by_entity.get(entity_id)
        grant = tokens.get(token) if token else None
        claim_list = _claims(ownership, entity_id)
        grant_controller = str(getattr(grant, "controller_id", "-")) if grant else "-"
        claim_controllers = sorted({str(getattr(item, "controller_id", "-"))
                                    for item in claim_list})
        shown = ",".join(claim_controllers) or "-"
        authorized = bool(
            grant is not None
            and str(getattr(grant, "entity_id", "")) == entity_id
            and any(
                str(getattr(item, "controller_id", "")) == grant_controller
                and entity_id in tuple(getattr(item, "entity_ids", ()))
                for item in claim_list
            )
        )
        if not authorized:
            failures.append(entity_id)
        print(f"{entity_id:<28}{('yes' if token else 'NO'):<7}{grant_controller:<34}"
              f"{len(claim_list):<7}{shown:<34}{'OK' if authorized else 'FAIL'}")

    print()
    if failures:
        print(f"entities that would be DENIED ({len(failures)}): {', '.join(failures)}")
    else:
        print("every entity is authority-authorized")

    print("\n=== controller-scoped grants (entity_id == '') ===")
    for token, grant in sorted(tokens.items()):
        if not str(getattr(grant, "entity_id", "")):
            print(f"  {token[:44]:<46} controller={getattr(grant, 'controller_id', '-')} "
                  f"entities={len(tuple(getattr(grant, 'entity_ids', ())))}")

    session.stop()
    session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
