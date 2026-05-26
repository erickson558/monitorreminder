from monitorreminder.config import default_profiles, load_config, save_config
from monitorreminder.models import AppConfig


def test_default_profiles_count() -> None:
    profiles = default_profiles()
    assert len(profiles) == 5
    assert profiles[0].id == 1
    assert profiles[-1].id == 5


def test_load_creates_defaults_when_missing(tmp_path) -> None:
    config = load_config(tmp_path / "config.json")
    assert len(config.profiles) == 5
    assert config.ui.language == "es"
    assert config.ui.window_state == "normal"


def test_save_and_load_round_trip(tmp_path) -> None:
    path = tmp_path / "config.json"
    config = AppConfig(profiles=default_profiles())
    config.ui.language = "en"
    config.ui.width = 1400
    config.ui.height = 900
    config.ui.pos_x = 40
    config.ui.pos_y = 30
    config.ui.window_state = "zoomed"
    config.profiles[0].name = "Desk"
    save_config(config, path)
    loaded = load_config(path)
    assert loaded.ui.language == "en"
    assert loaded.ui.width == 1400
    assert loaded.ui.height == 900
    assert loaded.ui.pos_x == 40
    assert loaded.ui.pos_y == 30
    assert loaded.ui.window_state == "zoomed"
    assert loaded.profiles[0].name == "Desk"