"""Tests for load_token function."""

import os
import sys
from unittest.mock import patch

import pytest

# Import after adding parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from queue_submit import load_token, SCRIPT_DIR


class TestLoadToken:
    """Test cases for load_token function."""

    def test_from_env_var(self, mock_env_token):
        """Test loading token from environment variable."""
        result = load_token()
        assert result == "test-token-12345"

    def test_env_var_takes_precedence(self, mock_env_token, tmp_path):
        """Test that env var takes precedence over .env file."""
        # Create .env file with different token
        env_file = tmp_path / ".env"
        env_file.write_text("AUTODL_TOKEN=env-file-token")

        with patch("queue_submit.SCRIPT_DIR", str(tmp_path)):
            result = load_token()
            assert result == "test-token-12345"  # Env var wins

    def test_no_env_no_envfile(self, mock_env_no_token, tmp_path):
        """Test when no env var and no .env file exists."""
        import queue_submit
        with patch.object(queue_submit, 'SCRIPT_DIR', str(tmp_path)):
            result = queue_submit.load_token()
            assert result is None

    def test_from_env_file(self, mock_env_no_token, tmp_path):
        """Test loading token from .env file."""
        import queue_submit
        env_file = tmp_path / ".env"
        env_file.write_text("AUTODL_TOKEN=file-token-123")

        with patch.object(queue_submit, 'SCRIPT_DIR', str(tmp_path)):
            result = queue_submit.load_token()
            assert result == "file-token-123"

    def test_env_file_with_whitespace(self, mock_env_no_token, tmp_path):
        """Test that whitespace is stripped from token."""
        import queue_submit
        env_file = tmp_path / ".env"
        env_file.write_text("AUTODL_TOKEN=  token-with-spaces  ")

        with patch.object(queue_submit, 'SCRIPT_DIR', str(tmp_path)):
            result = queue_submit.load_token()
            assert result == "token-with-spaces"

    def test_env_file_with_comments(self, mock_env_no_token, tmp_path):
        """Test .env file with comment lines."""
        import queue_submit
        env_file = tmp_path / ".env"
        env_file.write_text("""# This is a comment
AUTODL_TOKEN=comment-token
# Another comment
""")

        with patch.object(queue_submit, 'SCRIPT_DIR', str(tmp_path)):
            result = queue_submit.load_token()
            assert result == "comment-token"

    def test_env_file_with_empty_lines(self, mock_env_no_token, tmp_path):
        """Test .env file with empty lines."""
        import queue_submit
        env_file = tmp_path / ".env"
        env_file.write_text("""

AUTODL_TOKEN=empty-line-token

""")

        with patch.object(queue_submit, 'SCRIPT_DIR', str(tmp_path)):
            result = queue_submit.load_token()
            assert result == "empty-line-token"

    def test_env_file_missing_token_key(self, mock_env_no_token, tmp_path):
        """Test .env file without AUTODL_TOKEN key."""
        import queue_submit
        env_file = tmp_path / ".env"
        env_file.write_text("OTHER_VAR=value\nANOTHER_VAR=value2")

        with patch.object(queue_submit, 'SCRIPT_DIR', str(tmp_path)):
            result = queue_submit.load_token()
            assert result is None

    def test_env_file_multiple_equals(self, mock_env_no_token, tmp_path):
        """Test .env file with multiple = in value."""
        import queue_submit
        env_file = tmp_path / ".env"
        env_file.write_text("AUTODL_TOKEN=token=with=equals")

        with patch.object(queue_submit, 'SCRIPT_DIR', str(tmp_path)):
            result = queue_submit.load_token()
            assert result == "token=with=equals"

    def test_env_file_other_keys_ignored(self, mock_env_no_token, tmp_path):
        """Test that other keys in .env are ignored."""
        import queue_submit
        env_file = tmp_path / ".env"
        env_file.write_text("OTHER_KEY=other-value\nAUTODL_TOKEN=correct-token")

        with patch.object(queue_submit, 'SCRIPT_DIR', str(tmp_path)):
            result = queue_submit.load_token()
            assert result == "correct-token"

    def test_env_file_line_without_equals(self, mock_env_no_token, tmp_path):
        """Test .env file with line that has no equals sign (branch coverage)."""
        import queue_submit
        env_file = tmp_path / ".env"
        env_file.write_text("line_without_equals\nAUTODL_TOKEN=found-token")

        with patch.object(queue_submit, 'SCRIPT_DIR', str(tmp_path)):
            result = queue_submit.load_token()
            assert result == "found-token"

    def test_env_file_no_token_found(self, mock_env_no_token, tmp_path):
        """Test .env file exists but AUTODL_TOKEN not found (branch coverage)."""
        import queue_submit
        env_file = tmp_path / ".env"
        env_file.write_text("SOME_KEY=value\nANOTHER_KEY=value2")

        with patch.object(queue_submit, 'SCRIPT_DIR', str(tmp_path)):
            result = queue_submit.load_token()
            assert result is None
