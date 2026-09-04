from tapo_battery_guard.tray import make_icon


def test_tray_icon_is_a_square_image() -> None:
    icon = make_icon(charging=True, plugged=True)
    assert icon.size == (64, 64)
    assert icon.mode == "RGBA"


def test_tray_icon_can_be_exported_at_256() -> None:
    icon = make_icon(size=256)
    assert icon.size == (256, 256)
