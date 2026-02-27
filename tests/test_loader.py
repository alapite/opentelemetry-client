import importlib.metadata
import sys
import types

import pytest

from primes.distributions import loader
from primes.distributions.registry import registry


class DummyDistribution:
    metadata = {
        "name": "dummy",
        "version": "1.0.0",
        "description": "dummy",
        "author": "tests",
        "parameters": {},
    }

    def initialize(self, config):
        self.config = config

    def get_rate(self, time_elapsed: float, target_rps: float) -> float:
        return target_rps

    def validate(self) -> bool:
        return True


class FakeEntryPoint:
    def __init__(self, name: str, value: str) -> None:
        self.name = name
        self.value = value


def test_load_entry_points_discovers_plugins(monkeypatch):
    module_name = "tests.fake_plugin_module"
    fake_module = types.ModuleType(module_name)
    fake_module.DummyDistribution = DummyDistribution
    sys.modules[module_name] = fake_module

    def _entry_points(group: str):
        assert group == "primes.distributions"
        return [FakeEntryPoint("dummy", f"{module_name}:DummyDistribution")]

    monkeypatch.setattr(importlib.metadata, "entry_points", _entry_points)

    plugins = loader.load_entry_points("primes.distributions")
    assert plugins["dummy"] is DummyDistribution


def test_load_plugin_raises_when_missing():
    saved_registry = registry._plugins.copy()
    registry._plugins = {}

    try:
        with pytest.raises(ValueError):
            loader.load_plugin("missing")
    finally:
        registry._plugins = saved_registry


def test_load_plugins_registers_discovered(monkeypatch):
    module_name = "tests.fake_plugin_module2"
    fake_module = types.ModuleType(module_name)
    fake_module.DummyDistribution = DummyDistribution
    sys.modules[module_name] = fake_module

    def _entry_points(group: str):
        assert group == "primes.distributions"
        return [FakeEntryPoint("dummy", f"{module_name}:DummyDistribution")]

    saved_registry = registry._plugins.copy()
    registry._plugins = {}

    try:
        monkeypatch.setattr(importlib.metadata, "entry_points", _entry_points)
        loader.load_plugins()
        assert registry.get("dummy") is DummyDistribution
    finally:
        registry._plugins = saved_registry
