"""Tests for utility functions: log, output_json, fail."""

import json
import os
import sys
from io import StringIO
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from queue_submit import log, output_json, fail


class TestLog:
    """Test cases for log function."""

    def test_outputs_to_stderr(self, capsys):
        """Test that log outputs to stderr."""
        log("test message")
        captured = capsys.readouterr()
        assert captured.err == "test message\n"
        assert captured.out == ""

    def test_flushes_output(self):
        """Test that log flushes stderr."""
        # We can't easily test flush, but we can verify it doesn't raise
        log("flush test")

    def test_handles_special_characters(self, capsys):
        """Test log with special characters."""
        log("special: !@#$%^&*()")
        captured = capsys.readouterr()
        assert captured.err == "special: !@#$%^&*()\n"

    def test_handles_unicode(self, capsys):
        """Test log with unicode characters."""
        log("中文测试")
        captured = capsys.readouterr()
        assert captured.err == "中文测试\n"


class TestOutputJson:
    """Test cases for output_json function."""

    def test_outputs_valid_json(self, capsys):
        """Test that output_json outputs valid JSON."""
        data = {"key": "value", "number": 123}
        output_json(data)
        captured = capsys.readouterr()
        assert json.loads(captured.out) == data

    def test_outputs_to_stdout(self, capsys):
        """Test that output_json outputs to stdout."""
        output_json({"test": "data"})
        captured = capsys.readouterr()
        assert captured.out != ""
        assert captured.err == ""

    def test_uses_ensure_ascii_false(self, capsys):
        """Test that unicode characters are preserved."""
        data = {"message": "中文测试"}
        output_json(data)
        captured = capsys.readouterr()
        assert "中文测试" in captured.out

    def test_uses_indent(self, capsys):
        """Test that JSON is indented."""
        data = {"key": "value"}
        output_json(data)
        captured = capsys.readouterr()
        assert "  " in captured.out  # Has indentation

    def test_handles_nested_data(self, capsys):
        """Test with nested dictionary."""
        data = {"outer": {"inner": [1, 2, 3]}}
        output_json(data)
        captured = capsys.readouterr()
        assert json.loads(captured.out) == data

    def test_handles_empty_dict(self, capsys):
        """Test with empty dictionary."""
        output_json({})
        captured = capsys.readouterr()
        assert captured.out.strip() == "{}"


class TestFail:
    """Test cases for fail function."""

    def test_basic_fail(self, capsys):
        """Test basic fail with minimal arguments."""
        with pytest.raises(SystemExit) as exc_info:
            fail("error_type", "error message")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["status"] == "error"
        assert output["error_type"] == "error_type"
        assert output["message"] == "error message"

    def test_fail_with_details(self, capsys):
        """Test fail with details argument."""
        details = {"key": "value", "number": 42}
        with pytest.raises(SystemExit) as exc_info:
            fail("error_type", "error message", details)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["details"] == details

    def test_fail_with_custom_exit_code(self, capsys):
        """Test fail with custom exit code."""
        with pytest.raises(SystemExit) as exc_info:
            fail("error_type", "error message", exit_code=3)

        assert exc_info.value.code == 3

    def test_fail_exit_code_2(self, capsys):
        """Test fail with exit code 2."""
        with pytest.raises(SystemExit) as exc_info:
            fail("timeout", "timed out", exit_code=2)

        assert exc_info.value.code == 2

    def test_fail_no_details_key_when_none(self, capsys):
        """Test that details key is absent when details is None."""
        with pytest.raises(SystemExit):
            fail("error_type", "error message", details=None)

        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert "details" not in output

    def test_fail_outputs_to_stdout(self, capsys):
        """Test that fail outputs JSON to stdout."""
        with pytest.raises(SystemExit):
            fail("test", "test message")

        captured = capsys.readouterr()
        assert captured.out != ""
        assert json.loads(captured.out)  # Valid JSON
