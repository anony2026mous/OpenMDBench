"""Phase-0 single-controlled-USV configuration contract."""

from config.parallel_args import NavigationEnvArgs


def test_default_has_one_controlled_entity_per_environment() -> None:
    args = NavigationEnvArgs()
    assert args.max_num == 1
    assert args.controlled_entities_per_env == 1
    assert args.blue_num == 1
    assert args.red_num == 0
