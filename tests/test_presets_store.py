from pathlib import Path

import pytest

from primes.api.presets_store import PresetsStore


def test_create_list_update_delete_preset(tmp_path: Path) -> None:
    store = PresetsStore(tmp_path / "presets.json")
    preset = store.create_preset(
        name="smoke",
        config={
            "test_type": "linear",
            "duration_seconds": 10,
            "spawn_rate": 1.0,
            "user_count": 1,
        },
    )
    assert preset.id

    all_presets = store.list_presets()
    assert len(all_presets) == 1
    assert all_presets[0].name == "smoke"

    updated = store.update_preset(
        preset.id,
        name="smoke-2",
        config={
            "test_type": "linear",
            "duration_seconds": 20,
            "spawn_rate": 2.0,
            "user_count": 2,
        },
    )
    assert updated.name == "smoke-2"

    store.delete_preset(preset.id)
    assert store.list_presets() == []


def test_invalid_distribution_requires_target_rps(tmp_path: Path) -> None:
    store = PresetsStore(tmp_path / "presets.json")
    with pytest.raises(ValueError):
        store.create_preset(
            name="bad",
            config={
                "test_type": "distribution",
                "distribution": {"name": "constant", "config": {}},
            },
        )


def test_presets_file_env_override(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PRESETS_FILE", str(tmp_path / "presets.json"))
    from primes.api import config as api_config

    import importlib

    importlib.reload(api_config)

    assert str(tmp_path / "presets.json") == api_config.PRESETS_FILE


def test_create_uses_lock(tmp_path: Path) -> None:
    store = PresetsStore(tmp_path / "presets.json")

    class FakeLock:
        def __init__(self) -> None:
            self.entered = False

        def __enter__(self) -> None:
            self.entered = True

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    fake_lock = FakeLock()
    store._lock = fake_lock  # type: ignore[assignment]

    store.create_preset(
        name="lock-test",
        config={
            "test_type": "linear",
            "duration_seconds": 10,
            "spawn_rate": 1.0,
            "user_count": 1,
        },
    )

    assert fake_lock.entered is True


def test_atomic_write_preserves_file_on_replace_error(
    tmp_path: Path, monkeypatch
) -> None:
    path = tmp_path / "presets.json"
    store = PresetsStore(path)
    store.create_preset(
        name="smoke",
        config={
            "test_type": "linear",
            "duration_seconds": 10,
            "spawn_rate": 1.0,
            "user_count": 1,
        },
    )
    original = path.read_text(encoding="utf-8")

    def _raise_replace(src: Path, dst: Path) -> None:
        raise RuntimeError("replace failed")

    monkeypatch.setattr(store, "_replace", _raise_replace, raising=False)

    with pytest.raises(RuntimeError):
        store.create_preset(
            name="boom",
            config={
                "test_type": "linear",
                "duration_seconds": 20,
                "spawn_rate": 2.0,
                "user_count": 2,
            },
        )

    assert path.read_text(encoding="utf-8") == original
