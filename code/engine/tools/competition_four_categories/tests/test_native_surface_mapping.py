from tools.competition_four_categories.calibrate_surface import trial_package
from tools.competition_four_categories.surface_profile import PLATFORM_REF, DYNAMICS_REF
from tools.competition_four_categories.tests.test_native_candidate import session_from, close
from tools.competition_four_categories.validate_denial import submit_navigation


def test_candidate_surface_spheres_produce_native_collision_events():
    package = trial_package([6., 6.], PLATFORM_REF, DYNAMICS_REF, horizon=20, initial_speed=6.)
    second = package["scenario"]["entities"][1]
    second["initial_state"].update(position_m=[30., 0., 0.], velocity_mps=[-6., 0., 0.], heading_deg=270.)
    session, _ = session_from(package, "surface-proxy-collision")
    collisions = []
    try:
        for identifier, heading in (("unit.r01", 90.), ("unit.r02", 270.)):
            submit_navigation(session, identifier, "red", 0, {"valid_until_tick": 20, "payload": {"speed_mps": 6., "heading_deg": heading}})
        for tick in range(5):
            result = session.step(operation_id=f"tick-{tick}", expected_tick=tick)
            collisions.extend(c for r in result.world_receipt.motion_receipts for c in r.collision_events)
            if collisions: break
        assert collisions, "candidate configuration must not suppress real entity collisions"
    finally: close(session)
