"""Structural self-check for the MD-AD-006 scenario package and its LLM wiring.

Runs in seconds-to-a-minute and needs no episode, which matters because one
1800-tick arm costs 12-40 minutes.  It answers, before any expensive run:

  A. scenario structure   -- third neutral faction, both-direction neutral
                             relations, engine-enforced civilian ROE, civilian
                             entities/tags, per-entity controller slots whose
                             endpoint is the entity itself (zero-hop delivery);
  B. metric structure     -- civilians classify as ``civilian`` (never ``usv``)
                             and are excluded from both combat rosters, so the
                             raider denominator of the depth layer stays intact;
  C. prompt structure     -- the hybrid planner's ROE/target-classification
                             block is derived from THIS scenario's declared
                             timeline, and the graph prompt still renders with
                             every placeholder supplied;
  D. compile              -- the package still compiles through the engine's
                             formal V2 compiler;
  E. civilian transit      -- the neutral lane is actually under way (13 ticks).

Windows note: everything that constructs a session MUST live inside ``main()``
behind the ``__name__ == "__main__"`` guard.  The MMG solver runs in a
``multiprocessing`` child, and ``spawn`` re-imports ``__main__`` in that child —
top-level session code would therefore recurse and fail with "An attempt has been
made to start a new process before the current process has finished its
bootstrapping phase".

Usage:
    python _w1_structure_check.py [PUBLIC_ID]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import yaml

_ENGINE_DEFAULT = Path(__file__).resolve().parents[2] / "source-code" / "source_codes"
ROOT = Path(os.environ.get("OPENMDBENCH_ROOT") or _ENGINE_DEFAULT)
EVAL = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(EVAL))

PKG = ROOT / "scenarios" / "formal" / "ie_08_island_strike"

FAILURES: list[str] = []
CHECKS = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    mark = "ok  " if ok else "FAIL"
    print(f"  [{mark}] {label}" + (f" -- {detail}" if detail else ""))
    if not ok:
        FAILURES.append(label)


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def _catalog_index(bundle: str) -> tuple[dict[str, str], dict[str, dict]]:
    """(弹药引用 -> 武器引用, 武器引用 -> content) 索引，取自**指定**的 catalog 包。

    必须按包分别解析：IE 场景集用的是 `ie_set.yaml`，MD-AD-006 用的是
    `md_ad_006.yaml`，两者是各自独立的资源包（同名资源可以有不同的参数）。
    早先把两个包合并成一个字典，后加载的会覆盖先加载的 —— 于是 IE 场景的
    武器包线被拿 md_ad_006 的值去核对，真实的漂移反而被掩盖。
    """
    ammo_to_weapon: dict[str, str] = {}
    weapons: dict[str, dict] = {}
    path = ROOT / "catalog" / "v2" / bundle
    if not path.is_file():
        return ammo_to_weapon, weapons
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    for resource in payload.get("resources") or ():
        exact = f"{resource['id']}@{resource['version']}"
        content = resource.get("content") or {}
        if resource.get("resource_type") == "ammunition":
            ammo_to_weapon[exact] = str(content.get("weapon_ref"))
        elif resource.get("resource_type") == "weapons":
            weapons[exact] = dict(content)
    return ammo_to_weapon, weapons


def _bundle_for(package_name: str) -> str:
    """场景包 → 它自己的 catalog 资源包。"""
    return "ie_set.yaml" if package_name.startswith("ie_") else "md_ad_006.yaml"


def check_attacker_arming() -> None:
    """红方开火入口不变量 —— 第 11 轮根因的结构性防线。

    驱动层用 `AttackProfileDriverV2._maybe_fire` 按 `match_tag` 在实体标签上
    匹配 `attack.weapon_policies`；**匹配不到就永远不提交开火**。因此场景可以
    "编译通过、跑完 N tick、评分卡照常产出"，而红方全程一发未发 —— 这类缺陷
    不产生任何报错，只能靠不变量拦住。第 11 轮实测 IE-01..07 的 `fires_red`
    全为 0，红方单位飞到设施 200–300 m 上空仍然不开火。

    四项不变量：
      1. 有目标指派且有弹药的威胁实体，必须存在 `match_tag` 命中其标签的策略；
      2. 策略的 `weapon_ref` 必须等于该实体弹药所引用的武器；
      3. 策略射程窗口必须与武器资源声明的 min/max_range_m 一致（否则驱动的
         射程闸门与引擎包线不一致：要么空耗预算，要么在合法窗口内不开火）；
      4. 策略的 `shots` 不得超过实体申报弹药（超发即破坏弹药账目自洽）。
    """
    formal = ROOT / "scenarios" / "formal"
    packages = sorted(
        [item for item in formal.glob("ie_0*") if (item / "agents.yaml").is_file()]
        + [item for item in formal.glob("md_ad_006*")
           if (item / "agents.yaml").is_file()]
    )
    check("all 8 IE packages carry agents.yaml", len(packages) == 8,
          ",".join(item.name for item in packages))

    ammo_to_weapon, weapons = _catalog_index("ie_set.yaml")
    check("catalog resolves ammunition -> weapon", bool(ammo_to_weapon),
          f"{len(ammo_to_weapon)} ammunition resources")

    for package in packages:
        name = package.name
        # 按包解析各自的资源包（IE 场景集 / MD-AD-006 是两份独立 catalog）
        ammo_to_weapon, weapons = _catalog_index(_bundle_for(name))
        agents = yaml.safe_load((package / "agents.yaml").read_text(encoding="utf-8"))
        scenario = yaml.safe_load(
            (package / "scenario.yaml").read_text(encoding="utf-8"))["scenario"]
        policies = [
            item for item in (agents.get("attack") or {}).get("weapon_policies") or ()
            if isinstance(item, dict) and item.get("match_tag")
        ]
        if not policies:
            check(f"{name}: attacker declares weapon_policies", False,
                  "attack.weapon_policies missing -> the intruder never fires")
            continue

        intruders = [
            entity for entity in scenario["entities"]
            if entity["faction_id"] == "coalition.intruder"
            and any(str(tag).startswith("target.") for tag in entity.get("tags") or ())
        ]
        for event in scenario.get("events") or ():
            if event.get("event_type") != "spawn":
                continue
            blueprint = (event.get("payload") or {}).get("entity")
            if (isinstance(blueprint, dict)
                    and blueprint.get("faction_id") == "coalition.intruder"):
                intruders.append(blueprint)
        armed = [entity for entity in intruders if entity.get("ammunition")]

        unmatched: list[str] = []
        wrong_weapon: list[str] = []
        wrong_range: list[str] = []
        overspent: list[str] = []
        for entity in armed:
            tags = {str(tag) for tag in entity.get("tags") or ()}
            matched = [item for item in policies if str(item["match_tag"]) in tags]
            if not matched:
                unmatched.append(entity["id"])
                continue
            for ammo_ref, count in entity["ammunition"].items():
                weapon_ref = ammo_to_weapon.get(str(ammo_ref))
                if weapon_ref is None:
                    wrong_weapon.append(f"{entity['id']}:{ammo_ref} unresolvable")
                    continue
                policy = next((item for item in matched
                               if str(item.get("weapon_ref")) == weapon_ref), None)
                if policy is None:
                    wrong_weapon.append(f"{entity['id']}:{weapon_ref} has no policy")
                    continue
                weapon = weapons.get(weapon_ref) or {}
                if (float(policy["min_range_m"]) != float(weapon.get("min_range_m"))
                        or float(policy["max_range_m"])
                        != float(weapon.get("max_range_m"))):
                    wrong_range.append(
                        f"{entity['id']}: policy {policy['min_range_m']}-"
                        f"{policy['max_range_m']} vs weapon "
                        f"{weapon.get('min_range_m')}-{weapon.get('max_range_m')}")
                if int(policy.get("shots", 0)) > int(count):
                    overspent.append(
                        f"{entity['id']}: shots={policy.get('shots')} declared={count}")

        check(f"{name}: armed raiders found", bool(armed), f"{len(armed)} armed raiders")
        check(f"{name}: every armed raider has a matching fire policy",
              not unmatched, ",".join(sorted(set(unmatched))))
        check(f"{name}: policy weapon matches the declared ammunition",
              not wrong_weapon, "; ".join(sorted(set(wrong_weapon))))
        check(f"{name}: policy range window equals the weapon envelope",
              not wrong_range, "; ".join(sorted(set(wrong_range))))
        check(f"{name}: policy shots never exceed declared ammunition",
              not overspent, "; ".join(sorted(set(overspent))))


def main(public_id: str) -> int:
    scenario_payload = yaml.safe_load((PKG / "scenario.yaml").read_text(encoding="utf-8"))
    agents = yaml.safe_load((PKG / "agents.yaml").read_text(encoding="utf-8"))
    scenario = scenario_payload["scenario"]

    # ------------------------------------------------------------------
    section("A. scenario structure")

    factions = {item["id"] for item in scenario["factions"]}
    print(f"  declared factions: {','.join(sorted(factions))}")

    relations = {
        (item["source_faction_id"], item["target_faction_id"]): item["relation"]
        for item in scenario["relationships"]
    }
    check("defender <-> intruder is hostile",
          relations.get(("coalition.defender", "coalition.intruder")) == "hostile"
          and relations.get(("coalition.intruder", "coalition.defender")) == "hostile")

    roe = {
        (item["source_faction_id"], item["target_faction_id"]): item
        for item in scenario["world"]["roe_rules"]
    }
    for source, target in (("coalition.defender", "coalition.intruder"),
                           ("coalition.intruder", "coalition.defender")):
        rule = roe.get((source, target))
        check(f"ROE permits {source} engaging {target}",
              rule is not None and rule["engagement_permitted"] is True)

    # The neutral-civilian block is optional: the scenario may or may not declare a
    # third faction.  Either way the invariants that matter must hold.
    has_civilians = "coalition.civilian" in factions
    civilians = [e for e in scenario["entities"]
                 if e["faction_id"] == "coalition.civilian"]
    if has_civilians:
        check("neutral civilian faction declared with ships",
              len(civilians) == 3, f"{len(civilians)} ships")
        for source in ("coalition.defender", "coalition.intruder"):
            check(f"{source} -> civilian is neutral",
                  relations.get((source, "coalition.civilian")) == "neutral")
            check(f"civilian -> {source} is neutral",
                  relations.get(("coalition.civilian", source)) == "neutral")
            rule = roe.get((source, "coalition.civilian"))
            check(f"ROE forbids {source} engaging civilians",
                  rule is not None and rule["relationship"] == "neutral"
                  and rule["engagement_permitted"] is False)
        for entity in civilians:
            check(f"{entity['id']} tagged civilian+neutral",
                  {"civilian", "neutral"} <= set(entity["tags"]))
            check(f"{entity['id']} unarmed",
                  not entity.get("loadout_ref") and not entity.get("ammunition"))
            check(f"{entity['id']} has a communication ref (S3 endpoint contract)",
                  any(str(ref).startswith("communication.")
                      for ref in entity["component_refs"]))
    else:
        check("no civilian faction declared -> no civilian entities",
              not civilians, f"{len(civilians)} unexpected")
        check("no ROE rule references a civilian faction",
              not [key for key in roe if "civilian" in key[0] or "civilian" in key[1]],
              str(sorted(roe)))
        check("terminal rankings name no undeclared faction",
              all(set(rule["outcome"]["ranking"]) <= factions
                  for rule in scenario["mission_rules"]
                  if rule["outcome"].get("terminal")))

    def declared_entities() -> list[dict]:
        """Static entities plus every ``event_type: spawn`` blueprint.

        The intruder force is entirely spawn-declared, so counting only
        ``scenario["entities"]`` silently under-counts 17 of the 36 units.
        """
        found = list(scenario["entities"])
        for event in scenario["events"]:
            if event.get("event_type") != "spawn":
                continue
            blueprint = (event.get("payload") or {}).get("entity")
            if isinstance(blueprint, dict):
                found.append(blueprint)
        return found

    every_entity = declared_entities()
    slots = {item["id"]: item for item in scenario["controller_slots"]}
    check("one controller slot per declared entity (static + spawn)",
          len(slots) == len(every_entity),
          f"{len(slots)} slots / {len(every_entity)} declared entities")

    # Coverage is an id-level invariant, not a field lookup: spawn blueprints
    # deliberately drop ``controller_slot`` (they are taken over by the
    # per-entity intruder slots), so the authoritative question is "does some
    # slot select this entity id, and is its endpoint the entity itself?".
    endpoint_by_entity: dict[str, str] = {}
    for slot in scenario["controller_slots"]:
        endpoint = slot.get("controller_endpoint_ref")
        for entity_id in (slot.get("selector") or {}).get("entity_ids", ()) or ():
            endpoint_by_entity[str(entity_id)] = str(endpoint)

    uncovered = [entity["id"] for entity in every_entity
                 if entity["id"] not in endpoint_by_entity]
    check("every declared entity is selected by exactly one controller slot",
          not uncovered, ",".join(uncovered))
    check("every controller endpoint is the controlled entity itself (zero-hop)",
          all(endpoint_by_entity[entity["id"]] == entity["id"]
              for entity in every_entity if entity["id"] in endpoint_by_entity))

    # ------------------------------------------------------------------
    section("B. metric structure")

    from strategy_metrics import (  # noqa: PLC0415
        ROLE_CIVILIAN,
        ROLE_USV,
        classify_role,
    )

    check("civilian ship classifies as ROLE_CIVILIAN",
          classify_role("surface", ("civilian", "neutral")) == ROLE_CIVILIAN)
    check("a plain surface craft still classifies as ROLE_USV",
          classify_role("surface", ("usv", "defence")) == ROLE_USV)
    check("a civilian-tagged platform never counts as a usv",
          classify_role("surface", ("civilian",)) != ROLE_USV)

    roster_counts: dict[str, int] = {}
    for entity in every_entity:
        roster_counts[entity["faction_id"]] = roster_counts.get(entity["faction_id"], 0) + 1
    expected = {"coalition.defender": 16, "coalition.intruder": 17}
    if has_civilians:
        expected["coalition.civilian"] = 3
    check("combat rosters match the declared force structure",
          roster_counts == expected,
          f"actual={roster_counts} expected={expected}")
    check("no civilian-tagged entity sits inside a combat faction",
          not [entity["id"] for entity in every_entity
               if entity["faction_id"] in ("coalition.defender", "coalition.intruder")
               and "civilian" in {str(tag) for tag in entity.get("tags", ()) or ()}])
    check("terminal rankings cover every declared faction with unique ranks",
          all(set(rule["outcome"]["ranking"]) == factions
              and len(set(rule["outcome"]["ranking"].values()))
              == len(rule["outcome"]["ranking"])
              for rule in scenario["mission_rules"]
              if rule["outcome"].get("terminal")),
          "; ".join(f"{rule['id']}={rule['outcome']['ranking']}"
                    for rule in scenario["mission_rules"]
                    if rule["outcome"].get("terminal")))

    # ------------------------------------------------------------------
    section("C. prompt structure")

    import llm_planner  # noqa: PLC0415
    import run_episode  # noqa: PLC0415

    notes_ad006 = run_episode._build_roe_notes(agents["attack"]["timeline"])
    print("  --- roe_notes for MD-AD-006 ---")
    for line in notes_ad006.splitlines():
        print(f"      {line}")
    check("MD-AD-006 notes declare the strike waves hostile",
          "Declared HOSTILE strike waves" in notes_ad006
          and "wave-2 main strike" in notes_ad006)
    check("MD-AD-006 notes carry no borrowed tick numbers from another scenario",
          "115" not in notes_ad006 and "300" not in notes_ad006)
    if has_civilians:
        check("MD-AD-006 notes declare the civilian lane non-threat",
              "civilian transit lane" in notes_ad006
              and "do NOT intercept or fire" in notes_ad006)
        check("MD-AD-006 notes do NOT claim every contact is hostile",
              "EVERY detected contact is a hostile threat" not in notes_ad006)
    else:
        # The whole point of the fix: with no declared non-threat wave the planner
        # must be told outright that there is nothing to hold fire for.
        check("notes tell the planner every contact is a threat when the scenario "
              "declares no non-threat wave",
              "EVERY detected contact is a hostile threat" in notes_ad006)
        check("notes never contain a blanket do-not-intercept instruction",
              "do NOT intercept" not in notes_ad006)

    md_int_006 = ROOT / "scenarios" / "formal" / "md_int_006_saturation_roe" / "agents.yaml"
    if md_int_006.exists():
        other = yaml.safe_load(md_int_006.read_text(encoding="utf-8"))
        notes_other = run_episode._build_roe_notes(other["attack"]["timeline"])
        print("  --- roe_notes for MD-INT-006-SATURATION-ROE ---")
        for line in notes_other.splitlines():
            print(f"      {line}")
        check("a decoy/civilian scenario still gets non-threat bars",
              "NON-THREAT" in notes_other and "civilian" in notes_other.lower())
    else:
        check("MD-INT-006 agents.yaml available for the cross-scenario check", False,
              str(md_int_006))

    check("hybrid graph prompt template renders with all placeholders supplied",
          bool(llm_planner.PLANNER_USER_TEMPLATE_GRAPH.format(
              tick=0, graph="(g)", history="(h)", objective="(0,0)",
              weapon_range="500-8000", shore="(none)", roe_notes="(r)")))
    check("no hard-coded deception doctrine left in the shared template",
          "turn away at tick 115" not in llm_planner.PLANNER_USER_TEMPLATE_GRAPH
          and "spawn_tick ~300" not in llm_planner.PLANNER_USER_TEMPLATE_GRAPH)
    check("system prompt no longer names foreign wave ticks",
          "tick 115" not in llm_planner.PLANNER_SYSTEM_PROMPT
          and "wave-3" not in llm_planner.PLANNER_SYSTEM_PROMPT)

    # Target attribution must not depend on a hard-coded faction prefix: a third
    # faction introduces an id prefix that no earlier scenario had.
    known = ("defender.uav-01", "intruder.boat-01", "facility.comms",
             "civilian.ship-01")
    check("contact-id suffix resolves for a third-faction target",
          run_episode._contact_suffix(
              "sensor.contact.intruder.boat-01.civilian.ship-01", known)
          == "civilian.ship-01")
    check("contact-id suffix still resolves for a hostile target",
          run_episode._contact_suffix(
              "sensor.contact.defender.uav-01.intruder.boat-01", known)
          == "intruder.boat-01")
    check("contact-id suffix still resolves for a fixed facility",
          run_episode._contact_suffix(
              "sensor.contact.intruder.strike-comms-02.facility.comms", known)
          == "facility.comms")

    # Close the loop: the derived notes must survive construction of the real
    # planner, otherwise the fix never reaches the model.
    planner = llm_planner.LLMPlannerV2(
        config=run_episode.RulePlannerConfigV2(objective_m=(-1200.0, -200.0)),
        llm=None,
        prompt_context={"roe_notes": notes_ad006, "objective": "(-1200,-200)"},
    )
    check("derived roe_notes survive LLMPlannerV2 construction",
          planner._prompt_context.get("roe_notes") == notes_ad006)

    # ------------------------------------------------------------------
    section("D. compile through the engine")

    from openmdbench.scenarios.formal_v2 import compile_formal_scenario_v2  # noqa: PLC0415

    try:
        resolved, _catalog = compile_formal_scenario_v2(public_id)
        entity_ids = {entity.id for entity in resolved.entities}
        check("scenario compiles", True,
              f"resolved_hash={resolved.resolved_hash[:16]}...")
        rule_ids = {rule.id for rule in resolved.world.roe_rules}
        check("hostile ROE rules survive compilation",
              {"roe.defender-engage-intruder", "roe.intruder-engage-defender"} <= rule_ids,
              ",".join(sorted(rule_ids)))
        check("no controller slot is missing an endpoint",
              all((slot.values or {}).get("controller_endpoint_ref")
                  for slot in resolved.controller_slots),
              f"{len(resolved.controller_slots)} slots")
        if has_civilians:
            check("civilian entities survive compilation",
                  {"civilian.ship-01", "civilian.ship-02",
                   "civilian.ship-03"} <= entity_ids)
            check("civilian ROE rules survive compilation",
                  {"roe.defender-protect-civilian",
                   "roe.intruder-protect-civilian"} <= rule_ids)
    except Exception as error:  # noqa: BLE001 - the point is to report the failure
        check("scenario compiles", False, f"{type(error).__name__}: {error}")

    # ------------------------------------------------------------------
    section("E. civilian transit (13 ticks, seconds not minutes)")

    from openmdbench.sessions.formal_v2 import create_formal_session_v2  # noqa: PLC0415

    from civilian_transit import CivilianTransitDriverV2, civilian_routes  # noqa: PLC0415

    routes = civilian_routes(agents)
    if not has_civilians:
        check("no civilian lane declared -> the transit driver is not built",
              not routes, f"{routes}")
    else:
        check("agents.yaml declares the civilian lane", bool(routes),
              ", ".join(f"{k}:{v[0]:.0f}deg/{v[1]:.0f}mps"
                        for k, v in sorted(routes.items())))
    if not routes:
        # 早退分支同样要跑攻击方开火入口检查：它覆盖全部 8 个 IE 场景包，
        # 与"本场景有没有民用航道"无关。放在早退之后会被静默跳过。
        section("F. attacker arming (red fire entry point)")
        check_attacker_arming()
        section("summary")
        print(f"  {CHECKS - len(FAILURES)}/{CHECKS} checks passed "
              "(civilian transit probe skipped: no civilian lane)")
        for failure in FAILURES:
            print(f"    FAILED: {failure}")
        return 1 if FAILURES else 0
    try:
        session = create_formal_session_v2(public_id, session_id="audit.civilian", seed=7)
        session.load().start()
        driver = CivilianTransitDriverV2(faction_id="coalition.civilian", routes=routes)

        def civilian_positions() -> dict[str, tuple[float, float, float]]:
            return {
                str(item.id): tuple(float(v) for v in item.state.position_m)
                for item in session.world_view.entities_stable()
                if str(item.faction_id) == "coalition.civilian"
            }

        start_positions = civilian_positions()
        for _ in range(13):
            driver(session)
            session.step(operation_id=f"audit.civilian.{session.world_view.tick:08d}",
                         expected_tick=session.world_view.tick)
        end_positions = civilian_positions()
        session.stop()
        session.close()

        check("all three civilians exist after 13 ticks",
              set(start_positions) == set(routes), ",".join(sorted(start_positions)))
        for entity_id in sorted(routes):
            _heading, speed_mps = routes[entity_id]
            start = start_positions.get(entity_id)
            end = end_positions.get(entity_id)
            if start is None or end is None:
                check(f"{entity_id} moved", False, "missing at start or end")
                continue
            dy = end[1] - start[1]
            travelled = dy / 12.0  # 13 steps -> 12 intervals of motion
            # heading 180 == due south == negative y; the MMG ramp-up means the
            # first interval is slower, so only the direction and the ceiling are
            # asserted, not an exact displacement.
            check(f"{entity_id} is steaming south at a sane speed",
                  dy < -30.0 and travelled <= speed_mps + 1.0,
                  f"dy={dy:.0f} m over 12 s (~{travelled:.1f} m/s vs declared {speed_mps:.1f})")
        check("civilians carry no weapon loadout",
              all(not row.get("loadout_ref") for row in civilians))
    except Exception as error:  # noqa: BLE001 - report, do not mask
        check("civilian transit probe ran", False, f"{type(error).__name__}: {error}")

    # ------------------------------------------------------------------
    section("F. attacker arming (red fire entry point)")
    check_attacker_arming()

    # ------------------------------------------------------------------
    section("summary")
    print(f"  {CHECKS - len(FAILURES)}/{CHECKS} checks passed")
    for failure in FAILURES:
        print(f"    FAILED: {failure}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1 else "IE-08-ISLAND-STRIKE"))
