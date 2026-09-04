from tapo_battery_guard.config import AppConfig


def test_valid_config() -> None:
    config = AppConfig(host="192.168.1.10", username="user@example.com")
    assert config.validate() is None


def test_min_must_be_lower_than_max() -> None:
    config = AppConfig(host="192.168.1.10", username="user@example.com", min_percent=80, max_percent=80)
    assert config.validate() is not None
