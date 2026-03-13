"""Shared fixtures for tests."""

import json
import os
import tempfile
from unittest.mock import patch

import pytest
import responses

# Valid configuration fixture
VALID_CONFIG = {
    "name": "test-deployment",
    "deployment_type": "ReplicaSet",
    "replica_num": 2,
    "reuse_container": True,
    "container_template": {
        "gpu_name_set": ["RTX 4090"],
        "gpu_num": 1,
        "cuda_v": 118,
        "cpu_num_from": 1,
        "cpu_num_to": 4,
        "memory_size_from": 4,
        "memory_size_to": 16,
        "cmd": "python train.py",
        "price_from": 0.5,
        "price_to": 2.0,
        "image_uuid": "img-12345"
    }
}


@pytest.fixture
def valid_config():
    """Return a valid configuration dict."""
    import copy
    return copy.deepcopy(VALID_CONFIG)


@pytest.fixture
def valid_config_file(tmp_path):
    """Create a temporary valid config file."""
    config_file = tmp_path / "valid_config.json"
    config_file.write_text(json.dumps(VALID_CONFIG))
    return str(config_file)


@pytest.fixture
def mock_env_token():
    """Set and cleanup AUTODL_TOKEN environment variable."""
    original = os.environ.get("AUTODL_TOKEN")
    os.environ["AUTODL_TOKEN"] = "test-token-12345"
    yield "test-token-12345"
    if original is None:
        os.environ.pop("AUTODL_TOKEN", None)
    else:
        os.environ["AUTODL_TOKEN"] = original


@pytest.fixture
def mock_env_no_token():
    """Ensure AUTODL_TOKEN is not set."""
    original = os.environ.get("AUTODL_TOKEN")
    os.environ.pop("AUTODL_TOKEN", None)
    yield
    if original is not None:
        os.environ["AUTODL_TOKEN"] = original


@pytest.fixture
def temp_env_file(tmp_path):
    """Create a temporary .env file."""
    def _create_env(content):
        env_file = tmp_path / ".env"
        env_file.write_text(content)
        return str(env_file)
    return _create_env


@pytest.fixture
def mock_api_responses():
    """Mock all API responses."""
    with responses.RequestsMock() as rsps:
        # GPU stock API - default success response
        rsps.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/machine/gpu_stock",
            json={
                "code": "Success",
                "data": {
                    "RTX 4090": {"idle_gpu_num": 5, "total_gpu_num": 10},
                    "RTX 3090": {"idle_gpu_num": 0, "total_gpu_num": 8}
                }
            },
            status=200
        )

        # Image list API - default single page
        rsps.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/image/private/list",
            json={
                "code": "Success",
                "data": {
                    "list": [
                        {"image_uuid": "img-12345", "image_name": "test-image"}
                    ],
                    "max_page": 1
                }
            },
            status=200
        )

        # Deployment API - default success
        rsps.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/deployment",
            json={
                "code": "Success",
                "data": {"deployment_uuid": "deploy-abc123"}
            },
            status=200
        )

        yield rsps


@pytest.fixture
def mock_time():
    """Mock time.time and time.sleep for controlled testing."""
    with patch("queue_submit.time.time") as mock_time_func, \
         patch("queue_submit.time.sleep") as mock_sleep:
        # Default: time progresses by 1 second each call
        mock_time_func.side_effect = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        yield mock_time_func, mock_sleep
