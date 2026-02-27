# Load Distribution Plugins

This module provides a plugin system for load distribution strategies in the primes-client load testing framework.

## Overview

Plugins allow new load distribution patterns to be added without modifying the core codebase. Each distribution implements the `DistributionPlugin` abstract base class and is automatically discovered via entry points.

## Creating a New Distribution Plugin

### 1. Create the Plugin Class

```python
from primes.distributions import DistributionPlugin, DistributionMetadata, Parameter

class MyDistribution(DistributionPlugin):
    @property
    def metadata(self) -> DistributionMetadata:
        return DistributionMetadata(
            name="my-distribution",
            version="1.0.0",
            description="My custom distribution pattern",
            author="you@example.com",
            parameters={
                "target_rps": Parameter(
                    type="float",
                    default=100.0,
                    description="Target requests per second",
                    required=False,
                ),
            },
        )

    def initialize(self, config: dict[str, object]) -> None:
        self.config = config

    def get_rate(self, time_elapsed: float, target_rps: float) -> float:
        return target_rps * 0.5

    def validate(self) -> bool:
        return True
```

### 2. Register via entry_points

Add to `pyproject.toml`:

```toml
[project.entry-points."primes.distributions"]
my-distribution = "my_package.distributions:MyDistribution"
```

### 3. Usage

```python
from primes.distributions import load_plugin

plugin = load_plugin("my-distribution")
rate = plugin.get_rate(time_elapsed=10.0, target_rps=100.0)
```

## Plugin Interface

### DistributionPlugin ABC

All distribution plugins must inherit from `DistributionPlugin` and implement:

| Method | Description |
|--------|-------------|
| `metadata: DistributionMetadata` | Plugin information (name, version, parameters) |
| `initialize(config: dict)` | Configure the plugin with user parameters |
| `get_rate(time_elapsed, target_rps)` | Calculate request rate at given time |
| `validate() -> bool` | Validate configuration is valid |

### get_rate Method

The core strategy interface. Takes:
- `time_elapsed`: Seconds since test started
- `target_rps`: Target requests per second

Returns:
- Actual RPS to generate at this moment

Examples:
- Constant: always returns `target_rps`
- Linear ramp: returns `min(time_elapsed * ramp_rate, target_rps)`
- Poisson: returns `target_rps` with random variation

## Built-in Distributions

| Name | Description |
|------|-------------|
| `constant` | Constant rate throughout test |
| `linear` | Linear ramp-up to target RPS |
| `poisson` | Poisson-distributed arrivals |
| `step` | Step function (sudden changes) |
| `sine` | Sine wave pattern |

## API Reference

### Plugin Registry

```python
from primes.distributions import registry

# List all registered plugins
registry.list_all()  # ['constant', 'linear', ...]

# Check if plugin exists
'constant' in registry  # True

# Get plugin class
registry.get('constant')  # ConstantDistribution class
```

### Loader Functions

```python
from primes.distributions import (
    discover_plugins,  # Discover via entry_points
    load_plugin,       # Load and instantiate a plugin
    load_plugins,      # Discover and register all plugins
)
```

## Auto-Discovery

Plugins are auto-discovered on import if `PRIMES_AUTO_DISCOVER=true`:

```bash
PRIMES_AUTO_DISCOVER=true python -c "from primes.distributions import registry; print(registry.list_all())"
```

Or manually:

```python
from primes.distributions import load_plugins
load_plugins()
```
