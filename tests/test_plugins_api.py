import pytest
from fastapi.testclient import TestClient

from primes.api.main import app
from primes.distributions.loader import load_plugins


@pytest.fixture(scope="module")
def client():
    load_plugins()
    with TestClient(app) as c:
        yield c


def test_list_plugins(client):
    response = client.get("/api/v1/plugins")
    assert response.status_code == 200
    plugins = response.json()
    assert isinstance(plugins, list)
    assert len(plugins) > 0
    assert any(p["name"] == "constant" for p in plugins)


def test_get_plugin(client):
    response = client.get("/api/v1/plugins/constant")
    assert response.status_code == 200
    plugin = response.json()
    assert plugin["name"] == "constant"
    assert "version" in plugin
    assert "description" in plugin


def test_get_plugin_not_found(client):
    response = client.get("/api/v1/plugins/nonexistent")
    assert response.status_code == 404


def test_get_plugin_parameters(client):
    response = client.get("/api/v1/plugins/constant/parameters")
    assert response.status_code == 200
    params = response.json()
    assert isinstance(params, dict)


def test_list_distributions(client):
    response = client.get("/api/v1/distributions")
    assert response.status_code == 200
    distributions = response.json()
    assert isinstance(distributions, list)
    assert "constant" in distributions
    assert "linear" in distributions


def test_validate_distribution(client):
    response = client.post(
        "/api/v1/distributions/constant/validate", json={"config": {}}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is True


def test_validate_distribution_invalid(client):
    response = client.post(
        "/api/v1/distributions/nonexistent/validate", json={"config": {}}
    )
    assert response.status_code == 404


def test_instantiate_distribution(client):
    response = client.post("/api/v1/distributions/constant/instantiate")
    assert response.status_code == 200
    result = response.json()
    assert result["plugin_name"] == "constant"
    assert "instance_id" in result


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_constant_plugin_shows_rps_parameter(client):
    response = client.get("/api/v1/plugins/constant/parameters")
    assert response.status_code == 200
    params = response.json()
    assert "rps" in params
    assert params["rps"]["type"] == "float"
    assert params["rps"]["required"] is False


def test_validate_constant_distribution_valid_config(client):
    response = client.post(
        "/api/v1/distributions/constant/validate", json={"config": {"rps": 50.0}}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is True


def test_validate_constant_distribution_invalid_rps_negative(client):
    response = client.post(
        "/api/v1/distributions/constant/validate", json={"config": {"rps": -1}}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is False


def test_validate_constant_distribution_invalid_rps_zero(client):
    response = client.post(
        "/api/v1/distributions/constant/validate", json={"config": {"rps": 0}}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is False


# Linear Distribution Integration Tests


def test_linear_plugin_shows_ramp_duration_parameter(client):
    response = client.get("/api/v1/plugins/linear/parameters")
    assert response.status_code == 200
    params = response.json()
    assert "ramp_duration" in params
    assert params["ramp_duration"]["type"] == "float"
    assert params["ramp_duration"]["required"] is False
    assert params["ramp_duration"]["default"] == 60.0


def test_validate_linear_distribution_valid_config(client):
    response = client.post(
        "/api/v1/distributions/linear/validate",
        json={"config": {"ramp_duration": 30.0}},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is True


def test_validate_linear_distribution_valid_default(client):
    response = client.post("/api/v1/distributions/linear/validate", json={"config": {}})
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is True


def test_validate_linear_distribution_invalid_ramp_duration_zero(client):
    response = client.post(
        "/api/v1/distributions/linear/validate", json={"config": {"ramp_duration": 0.0}}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is False


def test_validate_linear_distribution_invalid_ramp_duration_negative(client):
    response = client.post(
        "/api/v1/distributions/linear/validate",
        json={"config": {"ramp_duration": -10.0}},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is False


def test_get_linear_plugin(client):
    response = client.get("/api/v1/plugins/linear")
    assert response.status_code == 200
    plugin = response.json()
    assert plugin["name"] == "linear"
    assert plugin["version"] == "1.0.0"
    assert "description" in plugin
    assert "ramp" in plugin["description"].lower()


# Poisson Distribution Integration Tests


def test_poisson_plugin_shows_lambda_param_and_variance_scale(client):
    """Test that poisson plugin shows lambda_param and variance_scale parameters."""
    response = client.get("/api/v1/plugins/poisson/parameters")
    assert response.status_code == 200
    params = response.json()
    assert "lambda_param" in params
    assert params["lambda_param"]["type"] == "float"
    assert params["lambda_param"]["required"] is False
    assert params["lambda_param"]["default"] is None
    assert "variance_scale" in params
    assert params["variance_scale"]["type"] == "float"
    assert params["variance_scale"]["required"] is False
    assert params["variance_scale"]["default"] == 1.0


def test_validate_poisson_distribution_valid_config(client):
    """Test validation with valid poisson configuration."""
    response = client.post(
        "/api/v1/distributions/poisson/validate",
        json={"config": {"lambda_param": 50.0, "variance_scale": 1.0}},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is True


def test_validate_poisson_distribution_valid_default(client):
    """Test validation with default poisson configuration."""
    response = client.post(
        "/api/v1/distributions/poisson/validate", json={"config": {}}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is True


def test_validate_poisson_distribution_invalid_lambda_param_negative(client):
    """Test validation fails with negative lambda_param."""
    response = client.post(
        "/api/v1/distributions/poisson/validate",
        json={"config": {"lambda_param": -10.0}},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is False


def test_validate_poisson_distribution_invalid_lambda_param_zero(client):
    """Test validation fails with zero lambda_param."""
    response = client.post(
        "/api/v1/distributions/poisson/validate",
        json={"config": {"lambda_param": 0.0}},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is False


def test_validate_poisson_distribution_invalid_variance_scale_negative(client):
    """Test validation fails with negative variance_scale."""
    response = client.post(
        "/api/v1/distributions/poisson/validate",
        json={"config": {"variance_scale": -1.0}},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is False


def test_validate_poisson_distribution_invalid_variance_scale_zero(client):
    """Test validation fails with zero variance_scale."""
    response = client.post(
        "/api/v1/distributions/poisson/validate",
        json={"config": {"variance_scale": 0.0}},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is False


def test_list_distributions_includes_poisson(client):
    """Test that poisson is listed in distributions."""
    response = client.get("/api/v1/distributions")
    assert response.status_code == 200
    distributions = response.json()
    assert "poisson" in distributions


def test_get_poisson_plugin(client):
    """Test getting poisson plugin details."""
    response = client.get("/api/v1/plugins/poisson")
    assert response.status_code == 200
    plugin = response.json()
    assert plugin["name"] == "poisson"
    assert plugin["version"] == "1.0.0"
    assert "description" in plugin
    assert "poisson" in plugin["description"].lower()


# Step Distribution Integration Tests


def test_step_plugin_shows_steps_and_default_rps_parameters(client):
    """Test that step plugin shows steps and default_rps parameters."""
    response = client.get("/api/v1/plugins/step/parameters")
    assert response.status_code == 200
    params = response.json()
    assert "steps" in params
    assert params["steps"]["type"] == "str"
    assert params["steps"]["required"] is False
    assert params["steps"]["default"] is None
    assert "default_rps" in params
    assert params["default_rps"]["type"] == "float"
    assert params["default_rps"]["required"] is False
    assert params["default_rps"]["default"] == 0.0


def test_validate_step_distribution_valid_config(client):
    """Test validation with valid step configuration."""
    response = client.post(
        "/api/v1/distributions/step/validate",
        json={"config": {"steps": "[[10, 50], [30, 100]]", "default_rps": 10}},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is True


def test_validate_step_distribution_valid_with_list(client):
    """Test validation with steps provided as list."""
    response = client.post(
        "/api/v1/distributions/step/validate",
        json={"config": {"steps": [[10, 50], [30, 100]], "default_rps": 10}},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is True


def test_validate_step_distribution_valid_default(client):
    """Test validation with default step configuration."""
    response = client.post("/api/v1/distributions/step/validate", json={"config": {}})
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is True


def test_validate_step_distribution_valid_no_steps(client):
    """Test validation with no steps but valid default_rps."""
    response = client.post(
        "/api/v1/distributions/step/validate", json={"config": {"default_rps": 10}}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is True


def test_validate_step_distribution_invalid_negative_time(client):
    """Test validation fails with negative time in steps."""
    response = client.post(
        "/api/v1/distributions/step/validate",
        json={"config": {"steps": "[[-1, 50]]", "default_rps": 10}},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is False


def test_validate_step_distribution_invalid_negative_rate(client):
    """Test validation fails with negative rate in steps."""
    response = client.post(
        "/api/v1/distributions/step/validate",
        json={"config": {"steps": "[[10, -50]]", "default_rps": 10}},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is False


def test_validate_step_distribution_invalid_negative_default_rps(client):
    """Test validation fails with negative default_rps."""
    response = client.post(
        "/api/v1/distributions/step/validate",
        json={"config": {"steps": "[[10, 50]]", "default_rps": -10}},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is False


def test_validate_step_distribution_invalid_malformed_steps(client):
    """Test validation fails with malformed steps JSON."""
    response = client.post(
        "/api/v1/distributions/step/validate",
        json={"config": {"steps": "[[10]]", "default_rps": 10}},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is False


def test_list_distributions_includes_step(client):
    """Test that step is listed in distributions."""
    response = client.get("/api/v1/distributions")
    assert response.status_code == 200
    distributions = response.json()
    assert "step" in distributions


def test_get_step_plugin(client):
    """Test getting step plugin details."""
    response = client.get("/api/v1/plugins/step")
    assert response.status_code == 200
    plugin = response.json()
    assert plugin["name"] == "step"
    assert plugin["version"] == "1.0.0"
    assert "description" in plugin
    assert "step" in plugin["description"].lower()
    assert "sudden" in plugin["description"].lower()


# Mix Distribution Integration Tests


def test_validate_mix_distribution_valid_config(client):
    response = client.post(
        "/api/v1/distributions/mix/validate",
        json={
            "config": {
                "target_rps": 40,
                "components": [
                    {
                        "weight": 0.7,
                        "distribution": {"name": "constant", "config": {"rps": 30}},
                    },
                    {
                        "weight": 0.3,
                        "distribution": {"name": "poisson", "config": {"lambda_param": 10}},
                    },
                ],
            }
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is True


def test_validate_mix_distribution_valid_json_string(client):
    response = client.post(
        "/api/v1/distributions/mix/validate",
        json={
            "config": {
                "components": (
                    '[{"weight": 1.0, "distribution": {"name": "constant", "config": {"rps": 10}}}]'
                )
            }
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is True


def test_validate_mix_distribution_invalid_components(client):
    response = client.post(
        "/api/v1/distributions/mix/validate",
        json={"config": {"components": [{"weight": -1, "distribution": {}}]}},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is False
    assert result["errors"]


# Sequence Distribution Integration Tests


def test_validate_sequence_distribution_valid_config(client):
    response = client.post(
        "/api/v1/distributions/sequence/validate",
        json={
            "config": {
                "post_behavior": "hold_last",
                "stages": [
                    {
                        "duration_seconds": 10,
                        "distribution": {"name": "linear", "config": {"ramp_duration": 10}},
                    },
                    {
                        "duration_seconds": 20,
                        "distribution": {"name": "constant", "config": {"rps": 50}},
                    },
                ],
            }
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is True


def test_validate_sequence_distribution_valid_json_string(client):
    response = client.post(
        "/api/v1/distributions/sequence/validate",
        json={
            "config": {
                "stages": (
                    '[{"duration_seconds": 5, "distribution": {"name": "constant", "config": {"rps": 10}}}]'
                )
            }
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is True


def test_validate_sequence_distribution_invalid_config(client):
    response = client.post(
        "/api/v1/distributions/sequence/validate",
        json={
            "config": {
                "post_behavior": "unknown",
                "stages": [{"duration_seconds": 0, "distribution": {"name": "", "config": {}}}],
            }
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is False
    assert result["errors"]


# Sine Distribution Integration Tests


def test_sine_plugin_shows_all_parameters(client):
    """Test that sine plugin shows all parameters."""
    response = client.get("/api/v1/plugins/sine/parameters")
    assert response.status_code == 200
    params = response.json()
    assert "period" in params
    assert params["period"]["type"] == "float"
    assert params["period"]["required"] is False
    assert params["period"]["default"] == 3600.0
    assert "amplitude" in params
    assert params["amplitude"]["type"] == "float"
    assert params["amplitude"]["required"] is False
    assert params["amplitude"]["default"] == 0.5
    assert "phase_shift" in params
    assert params["phase_shift"]["type"] == "float"
    assert params["phase_shift"]["required"] is False
    assert params["phase_shift"]["default"] == 0.0
    assert "base_rps" in params
    assert params["base_rps"]["type"] == "float"
    assert params["base_rps"]["required"] is False
    assert params["base_rps"]["default"] is None


def test_validate_sine_distribution_valid_config(client):
    """Test validation with valid sine configuration."""
    response = client.post(
        "/api/v1/distributions/sine/validate",
        json={"config": {"period": 60.0, "amplitude": 0.5, "phase_shift": 0.0}},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is True


def test_validate_sine_distribution_valid_default(client):
    """Test validation with default sine configuration."""
    response = client.post("/api/v1/distributions/sine/validate", json={"config": {}})
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is True


def test_validate_sine_distribution_invalid_amplitude_zero(client):
    """Test validation fails with amplitude = 0."""
    response = client.post(
        "/api/v1/distributions/sine/validate", json={"config": {"amplitude": 0.0}}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is False


def test_validate_sine_distribution_invalid_amplitude_greater_than_one(client):
    """Test validation fails with amplitude > 1."""
    response = client.post(
        "/api/v1/distributions/sine/validate", json={"config": {"amplitude": 1.5}}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is False


def test_validate_sine_distribution_invalid_amplitude_negative(client):
    """Test validation fails with negative amplitude."""
    response = client.post(
        "/api/v1/distributions/sine/validate", json={"config": {"amplitude": -0.5}}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is False


def test_validate_sine_distribution_invalid_period_zero(client):
    """Test validation fails with period = 0."""
    response = client.post(
        "/api/v1/distributions/sine/validate", json={"config": {"period": 0.0}}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is False


def test_validate_sine_distribution_invalid_period_negative(client):
    """Test validation fails with negative period."""
    response = client.post(
        "/api/v1/distributions/sine/validate", json={"config": {"period": -10.0}}
    )
    assert response.status_code == 200
    result = response.json()
    assert result["valid"] is False


def test_list_distributions_includes_sine(client):
    """Test that sine is listed in distributions."""
    response = client.get("/api/v1/distributions")
    assert response.status_code == 200
    distributions = response.json()
    assert "sine" in distributions


def test_get_sine_plugin(client):
    """Test getting sine plugin details."""
    response = client.get("/api/v1/plugins/sine")
    assert response.status_code == 200
    plugin = response.json()
    assert plugin["name"] == "sine"
    assert plugin["version"] == "1.0.0"
    assert "description" in plugin
    assert "sine" in plugin["description"].lower()
    assert "periodic" in plugin["description"].lower()


def test_list_distributions_includes_mix(client):
    response = client.get("/api/v1/distributions")
    assert response.status_code == 200
    distributions = response.json()
    assert "mix" in distributions


def test_validate_mix_distribution(client):
    response = client.post(
        "/api/v1/distributions/mix/validate",
        json={
            "config": {
                "components": [
                    {
                        "weight": 1.0,
                        "distribution": {"name": "constant", "config": {}},
                    }
                ]
            }
        },
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True


def test_list_distributions_includes_sequence(client):
    response = client.get("/api/v1/distributions")
    assert response.status_code == 200
    distributions = response.json()
    assert "sequence" in distributions


def test_validate_sequence_distribution(client):
    response = client.post(
        "/api/v1/distributions/sequence/validate",
        json={
            "config": {
                "stages": [
                    {
                        "duration_seconds": 5,
                        "distribution": {"name": "constant", "config": {}},
                    }
                ],
                "post_behavior": "hold_last",
            }
        },
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True
