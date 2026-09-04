from tapo_battery_guard.controller import PlugAction, decide_action


def test_turns_on_at_or_below_minimum() -> None:
    assert decide_action(20, False, 20, 80) is PlugAction.ON
    assert decide_action(5, False, 20, 80) is PlugAction.ON


def test_turns_off_at_or_above_maximum() -> None:
    assert decide_action(80, True, 20, 80) is PlugAction.OFF
    assert decide_action(100, True, 20, 80) is PlugAction.OFF


def test_holds_inside_the_band() -> None:
    assert decide_action(50, True, 20, 80) is PlugAction.HOLD
    assert decide_action(50, False, 20, 80) is PlugAction.HOLD


def test_does_not_toggle_when_already_in_desired_state() -> None:
    assert decide_action(15, True, 20, 80) is PlugAction.HOLD
    assert decide_action(95, False, 20, 80) is PlugAction.HOLD
