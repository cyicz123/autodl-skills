"""Tests for main function flow."""

import json
import os
import sys
from io import StringIO
from unittest.mock import patch, MagicMock

import pytest
import responses

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMainArguments:
    """Test command line argument parsing."""

    @responses.activate
    def test_missing_config_argument(self, capsys):
        """Test error when config argument is missing."""
        import queue_submit

        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, 'argv', ['queue_submit.py']):
                queue_submit.main()

        # argparse exits with code 2 for missing arguments
        assert exc_info.value.code == 2

    def test_interval_argument(self, tmp_path):
        """Test --interval argument is parsed."""
        import queue_submit

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"test": "config"}))

        with patch.object(sys, 'argv', ['queue_submit.py', str(config_file), '--interval', '60']):
            # Mock to exit early
            with patch.object(queue_submit, 'load_token', return_value='token'):
                with pytest.raises(SystemExit):
                    queue_submit.main()

    def test_timeout_argument(self, tmp_path):
        """Test --timeout argument is parsed."""
        import queue_submit

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"test": "config"}))

        with patch.object(sys, 'argv', ['queue_submit.py', str(config_file), '--timeout', '3600']):
            with patch.object(queue_submit, 'load_token', return_value='token'):
                with pytest.raises(SystemExit):
                    queue_submit.main()


class TestMainTokenMissing:
    """Test token missing scenarios."""

    def test_no_token_exits_with_error(self, tmp_path, capsys, mock_env_no_token):
        """Test exit when no token available."""
        import queue_submit

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps({"test": "config"}))

        with patch.object(sys, 'argv', ['queue_submit.py', str(config_file)]):
            with patch.object(queue_submit, 'SCRIPT_DIR', str(tmp_path)):
                # Ensure no .env file
                with pytest.raises(SystemExit) as exc_info:
                    queue_submit.main()

                assert exc_info.value.code == 1

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["error_type"] == "token_missing"


class TestMainConfigLoading:
    """Test configuration loading."""

    def test_config_file_not_found(self, tmp_path, mock_env_token, capsys):
        """Test error when config file doesn't exist."""
        import queue_submit

        nonexistent = tmp_path / "nonexistent.json"

        with patch.object(sys, 'argv', ['queue_submit.py', str(nonexistent)]):
            with pytest.raises(SystemExit) as exc_info:
                queue_submit.main()

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["error_type"] == "config_error"

    def test_invalid_json_config(self, tmp_path, mock_env_token, capsys):
        """Test error when config file has invalid JSON."""
        import queue_submit

        config_file = tmp_path / "invalid.json"
        config_file.write_text("not valid json{")

        with patch.object(sys, 'argv', ['queue_submit.py', str(config_file)]):
            with pytest.raises(SystemExit) as exc_info:
                queue_submit.main()

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["error_type"] == "config_error"


class TestMainValidationFailure:
    """Test config validation failure scenarios."""

    def test_validation_error_exits(self, tmp_path, mock_env_token, capsys):
        """Test exit on validation error."""
        import queue_submit

        invalid_config = {"name": "test"}  # Missing required fields

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(invalid_config))

        with patch.object(sys, 'argv', ['queue_submit.py', str(config_file)]):
            with pytest.raises(SystemExit) as exc_info:
                queue_submit.main()

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["error_type"] == "validation_error"


class TestMainImageNotFound:
    """Test image not found scenario."""

    @responses.activate
    def test_image_not_found_exits(self, tmp_path, mock_env_token, valid_config, capsys):
        """Test exit when image doesn't exist."""
        import queue_submit

        # Mock image list API returning empty
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/image/private/list",
            json={"code": "Success", "data": {"list": [], "max_page": 1}},
            status=200
        )

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(valid_config))

        with patch.object(sys, 'argv', ['queue_submit.py', str(config_file)]):
            with pytest.raises(SystemExit) as exc_info:
                queue_submit.main()

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["error_type"] == "image_not_found"


class TestMainGpuTypeNotFound:
    """Test GPU type not found scenario."""

    @responses.activate
    def test_gpu_type_not_found_exits(self, tmp_path, mock_env_token, valid_config, capsys):
        """Test exit when requested GPU types don't exist."""
        import queue_submit

        # Mock image list
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/image/private/list",
            json={
                "code": "Success",
                "data": {
                    "list": [{"image_uuid": "img-12345", "image_name": "test"}],
                    "max_page": 1
                }
            },
            status=200
        )

        # Mock GPU stock - different GPU than requested
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/machine/gpu_stock",
            json={
                "code": "Success",
                "data": {"RTX 3080": {"idle_gpu_num": 5, "total_gpu_num": 10}}
            },
            status=200
        )

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(valid_config))

        with patch.object(sys, 'argv', ['queue_submit.py', str(config_file)]):
            with pytest.raises(SystemExit) as exc_info:
                queue_submit.main()

            assert exc_info.value.code == 1

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["error_type"] == "gpu_type_not_found"


class TestMainPartialGpuType:
    """Test partial GPU type match scenario."""

    @responses.activate
    def test_partial_gpu_type_warns_and_continues(self, tmp_path, mock_env_token, capsys):
        """Test warning when some GPU types don't exist."""
        import queue_submit

        valid_config = {
            "name": "test",
            "deployment_type": "ReplicaSet",
            "replica_num": 1,
            "container_template": {
                "gpu_name_set": ["RTX 4090", "NonExistentGPU"],
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

        # Mock image list
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/image/private/list",
            json={
                "code": "Success",
                "data": {
                    "list": [{"image_uuid": "img-12345", "image_name": "test"}],
                    "max_page": 1
                }
            },
            status=200
        )

        # Mock GPU stock - only one of requested GPUs exists
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/machine/gpu_stock",
            json={
                "code": "Success",
                "data": {"RTX 4090": {"idle_gpu_num": 5, "total_gpu_num": 10}}
            },
            status=200
        )

        # Mock deployment success
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/deployment",
            json={"code": "Success", "data": {"deployment_uuid": "deploy-123"}},
            status=200
        )

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(valid_config))

        with patch.object(sys, 'argv', ['queue_submit.py', str(config_file)]):
            with pytest.raises(SystemExit) as exc_info:
                queue_submit.main()

            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        # Check warning in stderr
        assert "警告" in captured.err or "NonExistentGPU" in captured.err


class TestMainSuccessfulSubmit:
    """Test successful deployment submission."""

    @responses.activate
    def test_immediate_success(self, tmp_path, mock_env_token, valid_config, capsys):
        """Test successful submission on first attempt."""
        import queue_submit

        # Mock image list
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/image/private/list",
            json={
                "code": "Success",
                "data": {
                    "list": [{"image_uuid": "img-12345", "image_name": "test"}],
                    "max_page": 1
                }
            },
            status=200
        )

        # Mock GPU stock - GPU available
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/machine/gpu_stock",
            json={
                "code": "Success",
                "data": {"RTX 4090": {"idle_gpu_num": 5, "total_gpu_num": 10}}
            },
            status=200
        )

        # Mock deployment success
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/deployment",
            json={"code": "Success", "data": {"deployment_uuid": "deploy-abc123"}},
            status=200
        )

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(valid_config))

        with patch.object(sys, 'argv', ['queue_submit.py', str(config_file)]):
            with pytest.raises(SystemExit) as exc_info:
                queue_submit.main()

            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["status"] == "success"
        assert output["deployment_uuid"] == "deploy-abc123"


class TestMainPolling:
    """Test polling for GPU availability."""

    @responses.activate
    def test_poll_and_then_success(self, tmp_path, mock_env_token, valid_config, capsys):
        """Test polling until GPU becomes available."""
        import queue_submit

        # Mock image list
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/image/private/list",
            json={
                "code": "Success",
                "data": {
                    "list": [{"image_uuid": "img-12345", "image_name": "test"}],
                    "max_page": 1
                }
            },
            status=200
        )

        # First GPU stock check - no GPUs available
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/machine/gpu_stock",
            json={
                "code": "Success",
                "data": {"RTX 4090": {"idle_gpu_num": 0, "total_gpu_num": 10}}
            },
            status=200
        )

        # Second GPU stock check - GPU now available
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/machine/gpu_stock",
            json={
                "code": "Success",
                "data": {"RTX 4090": {"idle_gpu_num": 5, "total_gpu_num": 10}}
            },
            status=200
        )

        # Mock deployment success
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/deployment",
            json={"code": "Success", "data": {"deployment_uuid": "deploy-123"}},
            status=200
        )

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(valid_config))

        # Use interval 1 for test (minimum valid integer)
        with patch.object(sys, 'argv', ['queue_submit.py', str(config_file), '--interval', '1']):
            with pytest.raises(SystemExit) as exc_info:
                queue_submit.main()

            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        # Check that polling happened
        assert "GPU 不足" in captured.err or "资源可用" in captured.err


class TestMainTimeout:
    """Test timeout handling."""

    @responses.activate
    def test_timeout_exits(self, tmp_path, mock_env_token, valid_config, capsys):
        """Test exit when timeout is reached."""
        import queue_submit
        import time

        # Mock image list
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/image/private/list",
            json={
                "code": "Success",
                "data": {
                    "list": [{"image_uuid": "img-12345", "image_name": "test"}],
                    "max_page": 1
                }
            },
            status=200
        )

        # GPU always unavailable
        for _ in range(10):
            responses.add(
                responses.GET,
                "https://private.autodl.com/api/v1/dev/machine/gpu_stock",
                json={
                    "code": "Success",
                    "data": {"RTX 4090": {"idle_gpu_num": 0, "total_gpu_num": 10}}
                },
                status=200
            )

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(valid_config))

        # Use timeout 1 for test
        with patch.object(sys, 'argv', ['queue_submit.py', str(config_file), '--interval', '1', '--timeout', '1']):
            with pytest.raises(SystemExit) as exc_info:
                queue_submit.main()

            assert exc_info.value.code == 2

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["error_type"] == "timeout"

    @responses.activate
    def test_no_timeout_with_zero(self, tmp_path, mock_env_token, valid_config, capsys):
        """Test that timeout=0 means no timeout."""
        import queue_submit

        call_count = [0]

        def mock_gpu_stock(_token=None):
            call_count[0] += 1
            if call_count[0] < 3:
                return {"RTX 4090": {"idle": 0, "total": 10}}
            else:
                return {"RTX 4090": {"idle": 5, "total": 10}}

        # Mock image list
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/image/private/list",
            json={
                "code": "Success",
                "data": {
                    "list": [{"image_uuid": "img-12345", "image_name": "test"}],
                    "max_page": 1
                }
            },
            status=200
        )

        # Mock deployment success
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/deployment",
            json={"code": "Success", "data": {"deployment_uuid": "deploy-123"}},
            status=200
        )

        with patch('queue_submit.fetch_gpu_stock', side_effect=lambda token: mock_gpu_stock(token)):
            config_file = tmp_path / "config.json"
            config_file.write_text(json.dumps(valid_config))

            with patch.object(sys, 'argv', ['queue_submit.py', str(config_file), '--timeout', '0']):
                with pytest.raises(SystemExit) as exc_info:
                    queue_submit.main()

                assert exc_info.value.code == 0


class TestMainSubmitRetry:
    """Test deployment submission retry logic."""

    @responses.activate
    def test_submit_retry_then_success(self, tmp_path, mock_env_token, valid_config, capsys):
        """Test retry on submission failure then success."""
        import queue_submit

        # Mock image list
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/image/private/list",
            json={
                "code": "Success",
                "data": {
                    "list": [{"image_uuid": "img-12345", "image_name": "test"}],
                    "max_page": 1
                }
            },
            status=200
        )

        # GPU available
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/machine/gpu_stock",
            json={
                "code": "Success",
                "data": {"RTX 4090": {"idle_gpu_num": 5, "total_gpu_num": 10}}
            },
            status=200
        )

        # First submission fails
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/deployment",
            json={"code": "Error", "msg": "Temporary error"},
            status=200
        )

        # GPU still available
        responses.add(
            responses.GET,
            "https://private.autodl.com/api/v1/dev/machine/gpu_stock",
            json={
                "code": "Success",
                "data": {"RTX 4090": {"idle_gpu_num": 5, "total_gpu_num": 10}}
            },
            status=200
        )

        # Second submission succeeds
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/deployment",
            json={"code": "Success", "data": {"deployment_uuid": "deploy-123"}},
            status=200
        )

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(valid_config))

        with patch.object(sys, 'argv', ['queue_submit.py', str(config_file), '--interval', '1']):
            with pytest.raises(SystemExit) as exc_info:
                queue_submit.main()

            assert exc_info.value.code == 0

        captured = capsys.readouterr()
        # Check retry message
        assert "提交失败" in captured.err or "1/3" in captured.err

    @responses.activate
    def test_submit_max_retries_exceeded(self, tmp_path, mock_env_token, valid_config, capsys):
        """Test exit after max retries exceeded."""
        import queue_submit

        # Mock image list
        responses.add(
            responses.POST,
            "https://private.autodl.com/api/v1/dev/image/private/list",
            json={
                "code": "Success",
                "data": {
                    "list": [{"image_uuid": "img-12345", "image_name": "test"}],
                    "max_page": 1
                }
            },
            status=200
        )

        # GPU always available
        for _ in range(5):
            responses.add(
                responses.GET,
                "https://private.autodl.com/api/v1/dev/machine/gpu_stock",
                json={
                    "code": "Success",
                    "data": {"RTX 4090": {"idle_gpu_num": 5, "total_gpu_num": 10}}
                },
                status=200
            )

        # All submissions fail
        for _ in range(3):
            responses.add(
                responses.POST,
                "https://private.autodl.com/api/v1/dev/deployment",
                json={"code": "Error", "msg": "Persistent error"},
                status=200
            )

        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(valid_config))

        with patch.object(sys, 'argv', ['queue_submit.py', str(config_file), '--interval', '1']):
            with pytest.raises(SystemExit) as exc_info:
                queue_submit.main()

            assert exc_info.value.code == 3

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["error_type"] == "submission_error"
        assert "连续失败 3 次" in output["message"]
