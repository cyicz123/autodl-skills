"""Tests for dependency handling."""

import importlib
import json
import os
import subprocess
import sys
from io import StringIO
from unittest.mock import patch

import pytest


class TestRequestsDependency:
    """Test handling of missing requests dependency."""

    def test_missing_requests_exits_with_error(self, tmp_path, capsys):
        """Test that missing requests causes exit with code 3."""
        # We need to test the module-level code by simulating import error
        # Save original requests state
        had_requests = 'requests' in sys.modules
        original_requests = sys.modules.get('requests')

        try:
            # Remove requests from modules to simulate it not being installed
            if 'requests' in sys.modules:
                del sys.modules['requests']

            # Block requests from being imported
            import builtins
            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name == 'requests':
                    raise ImportError("No module named 'requests'")
                return original_import(name, *args, **kwargs)

            builtins.__import__ = mock_import

            try:
                # Import queue_submit with blocked requests
                if 'queue_submit' in sys.modules:
                    del sys.modules['queue_submit']

                import queue_submit
            except SystemExit as e:
                assert e.code == 3
            finally:
                builtins.__import__ = original_import

        finally:
            # Restore requests
            if had_requests and original_requests:
                sys.modules['requests'] = original_requests
            elif 'requests' in sys.modules:
                del sys.modules['requests']

    def test_missing_requests_outputs_json_error(self, tmp_path, capsys):
        """Test that missing requests outputs proper JSON error."""
        # Save stdout
        old_stdout = sys.stdout
        sys.stdout = StringIO()

        # Save original requests state
        had_requests = 'requests' in sys.modules
        original_requests = sys.modules.get('requests')

        try:
            # Remove requests from modules
            if 'requests' in sys.modules:
                del sys.modules['requests']

            # Block requests from being imported
            import builtins
            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name == 'requests':
                    raise ImportError("No module named 'requests'")
                return original_import(name, *args, **kwargs)

            builtins.__import__ = mock_import

            try:
                # Import queue_submit with blocked requests
                if 'queue_submit' in sys.modules:
                    del sys.modules['queue_submit']

                import queue_submit
            except SystemExit:
                pass
            finally:
                builtins.__import__ = original_import

            # Get output
            output = sys.stdout.getvalue()

        finally:
            sys.stdout = old_stdout
            # Restore requests
            if had_requests and original_requests:
                sys.modules['requests'] = original_requests

        # Parse and verify output
        error_output = json.loads(output)
        assert error_output["status"] == "error"
        assert error_output["error_type"] == "dependency_missing"
        assert "requests" in error_output["message"]
