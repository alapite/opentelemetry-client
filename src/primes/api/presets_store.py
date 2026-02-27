import json
import uuid
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from primes.api.routers.tests import StartTestRequest

@dataclass
class Preset:
    id: str
    name: str
    config: dict[str, Any]


class PresetsStore:
    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._lock = Lock()
        self._presets = self._load()

    def list_presets(self) -> list[Preset]:
        with self._lock:
            return list(self._presets)

    def create_preset(self, name: str, config: dict[str, Any]) -> Preset:
        with self._lock:
            self._validate_config(config)
            preset = Preset(id=str(uuid.uuid4()), name=name, config=dict(config))
            self._presets.append(preset)
            self._save()
            return preset

    def update_preset(self, preset_id: str, name: str, config: dict[str, Any]) -> Preset:
        with self._lock:
            self._validate_config(config)
            for idx, preset in enumerate(self._presets):
                if preset.id == preset_id:
                    updated = Preset(id=preset_id, name=name, config=dict(config))
                    self._presets[idx] = updated
                    self._save()
                    return updated
            raise KeyError(f"Preset '{preset_id}' not found")

    def delete_preset(self, preset_id: str) -> None:
        with self._lock:
            for idx, preset in enumerate(self._presets):
                if preset.id == preset_id:
                    del self._presets[idx]
                    self._save()
                    return
            raise KeyError(f"Preset '{preset_id}' not found")

    def _load(self) -> list[Preset]:
        if not self._file_path.exists():
            return []
        raw = json.loads(self._file_path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            return []
        presets: list[Preset] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            preset_id = item.get("id")
            name = item.get("name")
            config = item.get("config")
            if isinstance(preset_id, str) and isinstance(name, str) and isinstance(config, dict):
                presets.append(Preset(id=preset_id, name=name, config=config))
        return presets

    def _save(self) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        data = [
            {"id": preset.id, "name": preset.name, "config": preset.config}
            for preset in self._presets
        ]
        self._atomic_write(json.dumps(data, indent=2))

    def _validate_config(self, config: dict[str, Any]) -> None:
        request = StartTestRequest(**config)
        if request.distribution is not None:
            if request.target_rps is None:
                raise ValueError("target_rps is required when using a distribution")
            if request.num_requests is None and request.duration_seconds is None:
                raise ValueError(
                    "num_requests or duration_seconds is required when using a distribution"
                )

    def _atomic_write(self, payload: str) -> None:
        temp_path = self._file_path.with_suffix(
            f"{self._file_path.suffix}.{uuid.uuid4().hex}.tmp"
        )
        try:
            self._write_text(temp_path, payload)
            self._replace(temp_path, self._file_path)
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def _write_text(self, path: Path, payload: str) -> None:
        path.write_text(payload, encoding="utf-8")

    def _replace(self, src: Path, dst: Path) -> None:
        src.replace(dst)
