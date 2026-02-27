import os
from primes.config import from_env, validate, SERVICE_URL, BASE_URL


def test_from_env_returns_valid_config():
    config = from_env()
    assert "SERVICE_URL" in config
    assert "BASE_URL" in config
    assert config["SERVICE_URL"].startswith("http")


def test_validate_returns_true_when_service_url_set():
    os.environ["SERVICE_URL"] = "http://localhost:8080"
    try:
        assert validate() is True
    finally:
        del os.environ["SERVICE_URL"]


def test_validate_returns_true_without_service_url():
    if "SERVICE_URL" in os.environ:
        del os.environ["SERVICE_URL"]
    assert validate() is True


def test_service_url_defined():
    assert SERVICE_URL is not None
    assert SERVICE_URL.startswith("http")


def test_base_url_derived_from_service_url():
    assert BASE_URL.endswith("/api/primes")


def test_from_env_reads_latest_environment_values(monkeypatch):
    monkeypatch.setenv("SERVICE_URL", "http://example.local:9000")
    config = from_env()
    assert config["SERVICE_URL"] == "http://example.local:9000"
    assert config["BASE_URL"] == "http://example.local:9000/api/primes"
