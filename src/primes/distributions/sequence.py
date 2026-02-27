
from primes.distributions.base import DistributionMetadata, DistributionPlugin
from primes.distributions.utils import parse_json_or_list
from primes.distributions.loader import get_plugin_class


class SequenceDistribution(DistributionPlugin):
    """
    Sequence distribution - runs multiple distributions in order for fixed durations.

    Stages are applied sequentially. Post behavior can hold the last stage, return
    zero, or repeat the sequence.
    """

    stages: list[dict[str, object]]
    config: dict[str, object]
    _stage_plugins: list[DistributionPlugin]
    _stage_durations: list[float]
    _stage_starts: list[float]
    _total_duration: float
    post_behavior: str
    _parse_error: bool

    @property
    def metadata(self) -> DistributionMetadata:
        return DistributionMetadata(
            name="sequence",
            version="1.0.0",
            description="Sequence distribution - run distributions in order for fixed durations",
            author="primes-client",
            parameters={
                "stages": {
                    "type": "str",
                    "default": None,
                    "description": "JSON array of {duration_seconds, distribution{name, config}}",
                    "required": True,
                },
                "post_behavior": {
                    "type": "str",
                    "default": "hold_last",
                    "description": "Behavior after stages: hold_last, zero, or repeat",
                    "required": False,
                },
            },
        )

    def _set_post_behavior(self) -> None:
        post_behavior_value = self.config.get("post_behavior", "hold_last")
        if isinstance(post_behavior_value, str):
            self.post_behavior = post_behavior_value
            return
        self.post_behavior = "hold_last"
        self._parse_error = True

    def _parse_stages_data(self) -> list[object] | None:
        stages_value = self.config.get("stages")
        if stages_value is None:
            return []
        success, stages_data = parse_json_or_list(stages_value)
        if not success or not isinstance(stages_data, list):
            self._parse_error = True
            return None
        return stages_data

    def _parse_stage(
        self, stage: object
    ) -> tuple[dict[str, object], DistributionPlugin, float] | None:
        if not isinstance(stage, dict):
            self._parse_error = True
            return None

        duration_value = stage.get("duration_seconds")
        if not isinstance(duration_value, (int, float)):
            self._parse_error = True
            return None
        duration = float(duration_value)

        distribution_value = stage.get("distribution")
        if not isinstance(distribution_value, dict):
            self._parse_error = True
            return None

        name_value = distribution_value.get("name")
        if not isinstance(name_value, str):
            self._parse_error = True
            return None

        plugin_class = get_plugin_class(name_value)
        if plugin_class is None:
            self._parse_error = True
            return None

        config_value = distribution_value.get("config")
        if config_value is None:
            stage_config: dict[str, object] = {}
        elif isinstance(config_value, dict):
            stage_config = config_value
        else:
            self._parse_error = True
            return None

        plugin_instance = plugin_class()
        plugin_instance.initialize(stage_config)
        return stage, plugin_instance, duration

    def _finalize_stage_timeline(self) -> None:
        elapsed = 0.0
        for duration in self._stage_durations:
            self._stage_starts.append(elapsed)
            elapsed += duration
        self._total_duration = elapsed

    def _last_stage_index(self) -> int:
        return len(self._stage_plugins) - 1

    def _rate_for_stage(self, index: int, elapsed: float, target_rps: float) -> float:
        if index < 0:
            return max(0.0, target_rps)
        stage_start = self._stage_starts[index]
        return self._stage_plugins[index].get_rate(elapsed - stage_start, target_rps)

    def _elapsed_for_behavior(self, elapsed: float, target_rps: float) -> tuple[float, float] | None:
        if self.post_behavior == "repeat":
            return (elapsed % self._total_duration, target_rps)
        if elapsed < self._total_duration:
            return (elapsed, target_rps)
        if self.post_behavior == "zero":
            return (elapsed, 0.0)
        if self.post_behavior == "hold_last":
            return None
        return (elapsed, target_rps)

    def _find_active_stage(self, elapsed: float) -> int:
        for index, (stage_start, duration) in enumerate(
            zip(self._stage_starts, self._stage_durations)
        ):
            if elapsed < stage_start + duration:
                return index
        return self._last_stage_index()

    def initialize(self, config: dict[str, object]) -> None:
        self.config = config if config else {}
        self._parse_error = False
        self.stages = []
        self._stage_plugins = []
        self._stage_durations = []
        self._stage_starts = []
        self._total_duration = 0.0

        self._set_post_behavior()
        stages_data = self._parse_stages_data()
        if stages_data is None:
            return

        for stage in stages_data:
            parsed_stage = self._parse_stage(stage)
            if parsed_stage is None:
                continue
            raw_stage, plugin_instance, duration = parsed_stage
            self.stages.append(raw_stage)
            self._stage_plugins.append(plugin_instance)
            self._stage_durations.append(duration)

        self._finalize_stage_timeline()

    def get_rate(self, time_elapsed: float, target_rps: float) -> float:
        """Get the current rate based on the sequence of staged distributions.

        Args:
            time_elapsed: Time elapsed since test start in seconds
            target_rps: Target requests per second to use as fallback

        Returns:
            float: The rate for the current time step

        Note:
            - Stages are applied sequentially in order
            - After all stages complete, behavior depends on post_behavior:
              - "hold_last": Continue with the last stage's rate
              - "zero": Return 0 rate (stop generating requests)
              - "repeat": Restart the sequence from the beginning
            - Returns target_rps if configuration is invalid
        """
        # Guard against parse errors or invalid configuration
        if self._parse_error or not self._stage_plugins:
            return max(0.0, target_rps)

        # Guard against division by zero from total_duration
        if self._total_duration <= 0:
            return max(0.0, target_rps)

        elapsed_behavior = self._elapsed_for_behavior(time_elapsed, target_rps)
        if elapsed_behavior is None:
            return self._rate_for_stage(self._last_stage_index(), time_elapsed, target_rps)

        elapsed, fallback_rate = elapsed_behavior
        if fallback_rate == 0.0:
            return 0.0

        stage_index = self._find_active_stage(elapsed)
        return self._rate_for_stage(stage_index, elapsed, target_rps)

    def validate(self) -> bool:
        """Validate the sequence distribution configuration.

        Returns:
            bool: True if configuration is valid, False otherwise.

        Validations performed:
            - No parse errors in stage configuration
            - At least one stage is configured
            - post_behavior must be one of: hold_last, zero, or repeat
            - All stage durations must be positive (greater than 0)
            - All stage durations must be finite numbers (not NaN or infinity)
            - All stage plugins must be valid
            - Stage start times must be non-negative
            - Total duration must be greater than 0
            - config must be a dict if provided
        """
        # Check for parse errors from JSON or type conversion
        if self._parse_error:
            return False

        # Must have at least one stage
        if not self._stage_plugins:
            return False

        # Validate post_behavior
        if self.post_behavior not in {"hold_last", "zero", "repeat"}:
            return False

        for i, (duration, plugin) in enumerate(zip(self._stage_durations, self._stage_plugins)):
            if not self._validate_numeric_param(
                duration, positive=True, allow_none=False
            ):
                return False

            if i < len(self._stage_starts):
                start_time = self._stage_starts[i]
                if not self._validate_numeric_param(
                    start_time, non_negative=True, allow_none=False
                ):
                    return False

            if not plugin.validate():
                return False

        # Validate total duration
        if not self._validate_numeric_param(
            self._total_duration, positive=True, allow_none=False
        ):
            return False

        # Validate config structure
        return self._validate_config()
