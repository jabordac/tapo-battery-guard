import pytest

from tapo_battery_guard.tapo_client import list_outlet_choices, resolve_target


class FakePlug:
    def __init__(self, alias: str, device_id: str | None = None) -> None:
        self.alias = alias
        self.device_id = device_id or alias


class FakeStrip:
    def __init__(self, children: list[FakePlug]) -> None:
        self.alias = "Regleta"
        self.model = "HS300"
        self.children = children
        self._children = {child.device_id: child for child in children}

    def get_child_device(self, name_or_id: str):
        if name_or_id in self._children:
            return self._children[name_or_id]
        lowered = name_or_id.lower()
        for child in self.children:
            if child.alias.lower() == lowered:
                return child
        return None

    def get_plug_by_name(self, name: str):
        for child in self.children:
            if child.alias == name:
                return child
        raise ValueError(name)


def test_single_plug_ignores_child_spec() -> None:
    plug = FakePlug("P110")
    plug.children = []
    assert resolve_target(plug, "1") is plug


def test_strip_requires_child() -> None:
    strip = FakeStrip([FakePlug("Cargador"), FakePlug("Lámpara")])
    with pytest.raises(RuntimeError, match="6 conectores|2 conectores"):
        resolve_target(strip, "")


def test_strip_selects_one_based_index() -> None:
    first = FakePlug("Cargador")
    second = FakePlug("Lámpara")
    strip = FakeStrip([first, second])
    assert resolve_target(strip, "1") is first
    assert resolve_target(strip, "2") is second


def test_strip_selects_alias() -> None:
    lamp = FakePlug("Lámpara")
    strip = FakeStrip([FakePlug("Cargador"), lamp])
    assert resolve_target(strip, "Lámpara") is lamp


def test_strip_rejects_out_of_range() -> None:
    strip = FakeStrip([FakePlug("A"), FakePlug("B")])
    with pytest.raises(RuntimeError, match="no existe"):
        resolve_target(strip, "6")


def test_lists_one_based_outlets() -> None:
    strip = FakeStrip([FakePlug("Cargador"), FakePlug("Lámpara")])
    choices = list_outlet_choices(strip)
    assert [choice.spec for choice in choices] == ["1", "2"]
    assert choices[0].label == "1 · Cargador"
