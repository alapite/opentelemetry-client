import logging

from primes.settings import load_api_settings

logger = logging.getLogger(__name__)

_API_SETTINGS = load_api_settings()

API_SERVER_HOST = _API_SETTINGS.api_server_host
API_SERVER_PORT = _API_SETTINGS.api_server_port
API_WORKERS = _API_SETTINGS.api_workers
PRESETS_FILE = _API_SETTINGS.presets_file
