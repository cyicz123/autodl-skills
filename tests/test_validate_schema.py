"""Tests for validate_schema function."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from queue_submit import validate_schema


class TestValidateSchemaBasic:
    """Test basic field validation."""

    def test_valid_config_returns_empty_list(self, valid_config):
        """Test that valid config returns empty error list."""
        errors = validate_schema(valid_config)
        assert errors == []

    def test_missing_name(self, valid_config):
        """Test error when name is missing."""
        del valid_config["name"]
        errors = validate_schema(valid_config)
        assert "缺少 name" in errors

    def test_missing_deployment_type(self, valid_config):
        """Test error when deployment_type is missing."""
        del valid_config["deployment_type"]
        errors = validate_schema(valid_config)
        assert any("无效 deployment_type" in e for e in errors)

    def test_invalid_deployment_type(self, valid_config):
        """Test error with invalid deployment_type."""
        valid_config["deployment_type"] = "InvalidType"
        errors = validate_schema(valid_config)
        assert any("无效 deployment_type 'InvalidType'" in e for e in errors)


class TestValidateSchemaReplicaSet:
    """Test ReplicaSet specific validation."""

    def test_replicaset_needs_replica_num(self, valid_config):
        """Test ReplicaSet requires replica_num."""
        valid_config["deployment_type"] = "ReplicaSet"
        del valid_config["replica_num"]
        errors = validate_schema(valid_config)
        assert "ReplicaSet 需要 replica_num" in errors

    def test_replicaset_with_replica_num_is_valid(self, valid_config):
        """Test ReplicaSet with replica_num is valid."""
        valid_config["deployment_type"] = "ReplicaSet"
        valid_config["replica_num"] = 3
        errors = validate_schema(valid_config)
        assert errors == []


class TestValidateSchemaJob:
    """Test Job specific validation."""

    def test_job_needs_replica_num(self, valid_config):
        """Test Job requires replica_num."""
        valid_config["deployment_type"] = "Job"
        del valid_config["replica_num"]
        errors = validate_schema(valid_config)
        assert "Job 需要 replica_num" in errors

    def test_job_needs_parallelism_num(self, valid_config):
        """Test Job requires parallelism_num."""
        valid_config["deployment_type"] = "Job"
        valid_config["replica_num"] = 2
        # parallelism_num is missing
        errors = validate_schema(valid_config)
        assert "Job 需要 parallelism_num" in errors

    def test_job_with_both_nums_is_valid(self, valid_config):
        """Test Job with replica_num and parallelism_num is valid."""
        valid_config["deployment_type"] = "Job"
        valid_config["replica_num"] = 2
        valid_config["parallelism_num"] = 2
        errors = validate_schema(valid_config)
        assert errors == []


class TestValidateSchemaContainer:
    """Test Container specific validation."""

    def test_container_does_not_need_replica_num(self, valid_config):
        """Test Container doesn't require replica_num."""
        valid_config["deployment_type"] = "Container"
        del valid_config["replica_num"]
        errors = validate_schema(valid_config)
        # Should not have replica_num error
        assert not any("replica_num" in e for e in errors)


class TestValidateSchemaContainerTemplate:
    """Test container_template validation."""

    def test_missing_container_template(self, valid_config):
        """Test error when container_template is missing."""
        del valid_config["container_template"]
        errors = validate_schema(valid_config)
        assert "缺少 container_template" in errors

    def test_container_template_is_none(self, valid_config):
        """Test error when container_template is None."""
        valid_config["container_template"] = None
        errors = validate_schema(valid_config)
        assert "缺少 container_template" in errors

    def test_container_template_is_empty_dict(self, valid_config):
        """Test error when container_template is empty dict (falsy value)."""
        valid_config["container_template"] = {}
        errors = validate_schema(valid_config)
        # Empty dict is falsy, so it returns "缺少 container_template"
        assert "缺少 container_template" in errors


class TestValidateSchemaRequiredFields:
    """Test all required fields in container_template."""

    REQUIRED_FIELDS = [
        "gpu_name_set", "gpu_num", "cuda_v",
        "cpu_num_from", "cpu_num_to",
        "memory_size_from", "memory_size_to",
        "cmd", "price_from", "price_to", "image_uuid",
    ]

    @pytest.mark.parametrize("field", REQUIRED_FIELDS)
    def test_missing_required_field(self, valid_config, field):
        """Test error when each required field is missing."""
        del valid_config["container_template"][field]
        errors = validate_schema(valid_config)
        assert any(f"container_template 缺少" in e and field in e for e in errors)

    def test_multiple_missing_fields_reported(self, valid_config):
        """Test that multiple missing fields are all reported."""
        del valid_config["container_template"]["gpu_num"]
        del valid_config["container_template"]["cuda_v"]
        errors = validate_schema(valid_config)
        # Both fields should be mentioned in a single error
        error_str = errors[0]
        assert "gpu_num" in error_str
        assert "cuda_v" in error_str


class TestValidateSchemaRangeValidation:
    """Test range validation in container_template."""

    def test_cpu_from_greater_than_to(self, valid_config):
        """Test error when cpu_num_from > cpu_num_to."""
        valid_config["container_template"]["cpu_num_from"] = 8
        valid_config["container_template"]["cpu_num_to"] = 4
        errors = validate_schema(valid_config)
        assert any("cpu_num_from(8) > cpu_num_to(4)" in e for e in errors)

    def test_cpu_from_equal_to_to_is_valid(self, valid_config):
        """Test valid when cpu_num_from == cpu_num_to."""
        valid_config["container_template"]["cpu_num_from"] = 4
        valid_config["container_template"]["cpu_num_to"] = 4
        errors = validate_schema(valid_config)
        assert errors == []

    def test_memory_from_greater_than_to(self, valid_config):
        """Test error when memory_size_from > memory_size_to."""
        valid_config["container_template"]["memory_size_from"] = 32
        valid_config["container_template"]["memory_size_to"] = 16
        errors = validate_schema(valid_config)
        assert any("memory_size_from(32) > memory_size_to(16)" in e for e in errors)

    def test_price_from_greater_than_to(self, valid_config):
        """Test error when price_from > price_to."""
        valid_config["container_template"]["price_from"] = 2.0
        valid_config["container_template"]["price_to"] = 1.0
        errors = validate_schema(valid_config)
        assert any("price_from(2.0) > price_to(1.0)" in e for e in errors)


class TestValidateSchemaGpuValidation:
    """Test GPU related validation."""

    def test_gpu_num_zero(self, valid_config):
        """Test error when gpu_num is 0."""
        valid_config["container_template"]["gpu_num"] = 0
        errors = validate_schema(valid_config)
        assert any("gpu_num(0) 必须 >= 1" in e for e in errors)

    def test_gpu_num_negative(self, valid_config):
        """Test error when gpu_num is negative."""
        valid_config["container_template"]["gpu_num"] = -1
        errors = validate_schema(valid_config)
        assert any("gpu_num(-1) 必须 >= 1" in e for e in errors)

    def test_gpu_num_one_is_valid(self, valid_config):
        """Test valid when gpu_num is 1."""
        valid_config["container_template"]["gpu_num"] = 1
        errors = validate_schema(valid_config)
        assert errors == []

    def test_gpu_num_positive_is_valid(self, valid_config):
        """Test valid when gpu_num is positive."""
        valid_config["container_template"]["gpu_num"] = 8
        errors = validate_schema(valid_config)
        assert errors == []

    def test_empty_gpu_name_set(self, valid_config):
        """Test error when gpu_name_set is empty."""
        valid_config["container_template"]["gpu_name_set"] = []
        errors = validate_schema(valid_config)
        assert "gpu_name_set 不能为空" in errors

    def test_single_gpu_name_is_valid(self, valid_config):
        """Test valid with single GPU name."""
        valid_config["container_template"]["gpu_name_set"] = ["RTX 4090"]
        errors = validate_schema(valid_config)
        assert errors == []

    def test_multiple_gpu_names_is_valid(self, valid_config):
        """Test valid with multiple GPU names."""
        valid_config["container_template"]["gpu_name_set"] = ["RTX 4090", "RTX 3090"]
        errors = validate_schema(valid_config)
        assert errors == []


class TestValidateSchemaCudaValidation:
    """Test CUDA version validation."""

    def test_valid_cuda_111(self, valid_config):
        """Test valid with CUDA 111."""
        valid_config["container_template"]["cuda_v"] = 111
        errors = validate_schema(valid_config)
        assert errors == []

    def test_valid_cuda_113(self, valid_config):
        """Test valid with CUDA 113."""
        valid_config["container_template"]["cuda_v"] = 113
        errors = validate_schema(valid_config)
        assert errors == []

    def test_valid_cuda_118(self, valid_config):
        """Test valid with CUDA 118."""
        valid_config["container_template"]["cuda_v"] = 118
        errors = validate_schema(valid_config)
        assert errors == []

    def test_valid_cuda_122(self, valid_config):
        """Test valid with CUDA 122."""
        valid_config["container_template"]["cuda_v"] = 122
        errors = validate_schema(valid_config)
        assert errors == []

    def test_invalid_cuda_version(self, valid_config):
        """Test error with invalid CUDA version."""
        valid_config["container_template"]["cuda_v"] = 999
        errors = validate_schema(valid_config)
        assert any("cuda_v(999) 不在已知版本列表" in e for e in errors)

    def test_cuda_version_not_in_known_list(self, valid_config):
        """Test error with CUDA version not in known list."""
        valid_config["container_template"]["cuda_v"] = 100
        errors = validate_schema(valid_config)
        assert any("cuda_v(100) 不在已知版本列表" in e for e in errors)


class TestValidateSchemaMultipleErrors:
    """Test multiple errors reported together."""

    def test_multiple_validation_errors(self, valid_config):
        """Test that multiple errors are all reported."""
        valid_config["container_template"]["cpu_num_from"] = 10
        valid_config["container_template"]["cpu_num_to"] = 2
        valid_config["container_template"]["gpu_num"] = 0
        valid_config["container_template"]["gpu_name_set"] = []
        errors = validate_schema(valid_config)
        # Should have 3 errors
        assert len(errors) == 3
        assert any("cpu_num_from" in e for e in errors)
        assert any("gpu_num" in e for e in errors)
        assert any("gpu_name_set" in e for e in errors)

    def test_missing_template_returns_early(self, valid_config):
        """Test that missing container_template returns early without checking fields."""
        del valid_config["container_template"]
        errors = validate_schema(valid_config)
        # Should only have the missing container_template error
        assert len(errors) == 1
        assert "缺少 container_template" in errors[0]

    def test_missing_template_field_returns_early(self, valid_config):
        """Test that missing required field returns early without checking ranges."""
        del valid_config["container_template"]["gpu_num"]
        # Also set invalid range
        valid_config["container_template"]["cpu_num_from"] = 10
        valid_config["container_template"]["cpu_num_to"] = 2
        errors = validate_schema(valid_config)
        # Should only have the missing field error
        assert len(errors) == 1
        assert "container_template 缺少" in errors[0]
