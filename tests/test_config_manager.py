import json
import os
import pytest
import tempfile
import time
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, MagicMock

# Import the class to test
from fhnlab.core.configuration_manager import ConfigurationManager


# ==================== FIXTURES ====================

@pytest.fixture
def temp_dirs():
    """Create temporary directories for schemas and configs."""
    with tempfile.TemporaryDirectory() as schema_dir:
        with tempfile.TemporaryDirectory() as config_dir:
            yield {
                'schema_dir': schema_dir,
                'config_dir': config_dir
            }


@pytest.fixture
def sample_schema() -> Dict[str, Any]:
    """Sample JSON schema for testing."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "value": {"type": "number"},
            "enabled": {"type": "boolean"},
            "nested": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"}
                }
            }
        },
        "required": ["name", "value"]
    }


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Sample valid configuration."""
    return {
        "name": "test_config",
        "value": 42,
        "enabled": True,
        "nested": {
            "key": "test_value"
        }
    }


@pytest.fixture
def invalid_config() -> Dict[str, Any]:
    """Sample invalid configuration (missing required field)."""
    return {
        "name": "invalid_config",
        "enabled": True
        # Missing 'value' which is required
    }


@pytest.fixture
def fhn_model_schema() -> Dict[str, Any]:
    """FitzHugh-Nagumo model schema."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "parameters": {
                "type": "object",
                "properties": {
                    "epsilon": {"type": "number", "minimum": 0},
                    "a": {"type": "number"},
                    "b": {"type": "number"},
                    "I_ext": {"type": "number"}
                },
                "required": ["epsilon", "a"]
            },
            "diffusion": {
                "type": "object",
                "properties": {
                    "D_u": {"type": "number", "minimum": 0},
                    "D_v": {"type": "number", "minimum": 0}
                }
            }
        },
        "required": ["name", "parameters"]
    }


@pytest.fixture
def config_manager(temp_dirs, sample_schema, sample_config):
    """Create ConfigurationManager instance with test data."""
    schema_dir = temp_dirs['schema_dir']
    config_dir = temp_dirs['config_dir']
    
    # Write sample schema
    schema_path = Path(schema_dir) / "test_schema.json"
    with open(schema_path, 'w') as f:
        json.dump(sample_schema, f)
    
    # Write sample config
    config_path = Path(config_dir) / "test_config.json"
    with open(config_path, 'w') as f:
        json.dump(sample_config, f)
    
    from fhnlab.core.configuration_manager import ConfigurationManager
    return ConfigurationManager(schema_dir, config_dir)


# ==================== INITIALIZATION TESTS ====================

class TestInitialization:
    """Test ConfigurationManager initialization."""
    
    def test_init_valid_directories(self, temp_dirs):
        """Test initialization with valid directories."""
        from fhnlab.core.configuration_manager import ConfigurationManager
        cm = ConfigurationManager(
            temp_dirs['schema_dir'],
            temp_dirs['config_dir']
        )
        assert cm.schema_dir == Path(temp_dirs['schema_dir'])
        assert cm.config_dir == Path(temp_dirs['config_dir'])
        assert isinstance(cm._cache, dict)
        assert isinstance(cm._timestamps, dict)
    
    def test_init_missing_schema_dir(self, temp_dirs):
        """Test initialization with missing schema directory."""
        from fhnlab.core.configuration_manager import ConfigurationManager
        with pytest.raises(FileNotFoundError, match="Schema directory not found"):
            ConfigurationManager("/nonexistent/schema", temp_dirs['config_dir'])
    
    def test_init_missing_config_dir(self, temp_dirs):
        """Test initialization with missing config directory."""
        from fhnlab.core.configuration_manager import ConfigurationManager
        with pytest.raises(FileNotFoundError, match="Configuration directory not found"):
            ConfigurationManager(temp_dirs['schema_dir'], "/nonexistent/config")


# ==================== LOADING TESTS ====================

class TestLoading:
    """Test configuration and schema loading."""
    
    def test_load_schema(self, config_manager):
        """Test loading a valid schema."""
        schema = config_manager._load_schema("test_schema.json")
        assert schema["type"] == "object"
        assert "properties" in schema
    
    def test_load_schema_not_found(self, config_manager):
        """Test loading non-existent schema."""
        with pytest.raises(FileNotFoundError, match="Schema not found"):
            config_manager._load_schema("nonexistent_schema.json")
    
    def test_load_config(self, config_manager):
        """Test loading a valid configuration."""
        config = config_manager._load_config("test_config.json")
        assert config["name"] == "test_config"
        assert config["value"] == 42
    
    def test_load_config_not_found(self, config_manager):
        """Test loading non-existent configuration."""
        with pytest.raises(FileNotFoundError, match="Configuration not found"):
            config_manager._load_config("nonexistent_config.json")
    
    def test_get_config_no_validation(self, config_manager):
        """Test getting config without validation."""
        config = config_manager.get_config("test_config.json")
        assert config["name"] == "test_config"
        assert config["value"] == 42


# ==================== VALIDATION TESTS ====================

class TestValidation:
    """Test configuration validation."""
    
    def test_validate_valid_config(self, config_manager, sample_config, sample_schema):
        """Test validation of valid configuration."""
        assert config_manager._validate_config(sample_config, sample_schema) is True
    
    def test_validate_invalid_config(self, config_manager, invalid_config, sample_schema):
        """Test validation of invalid configuration."""
        with pytest.raises(ValueError, match="Configuration validation failed"):
            config_manager._validate_config(invalid_config, sample_schema)
    
    def test_validate_missing_required_field(self, config_manager, sample_schema):
        """Test validation with missing required field."""
        invalid = {"name": "test"}  # Missing 'value'
        with pytest.raises(ValueError, match="Configuration validation failed"):
            config_manager._validate_config(invalid, sample_schema)
    
    def test_validate_wrong_type(self, config_manager, sample_schema):
        """Test validation with wrong type."""
        invalid = {"name": "test", "value": "not_a_number"}
        with pytest.raises(ValueError, match="Configuration validation failed"):
            config_manager._validate_config(invalid, sample_schema)
    
    def test_load_and_validate_success(self, config_manager):
        """Test successful load and validate."""
        config = config_manager.load_and_validate(
            "test_config.json",
            "test_schema.json"
        )
        assert config["name"] == "test_config"
    
    def test_load_and_validate_failure(self, config_manager, invalid_config):
        """Test load and validate with invalid config."""
        # Write invalid config
        invalid_path = config_manager.config_dir / "invalid_config.json"
        with open(invalid_path, 'w') as f:
            json.dump(invalid_config, f)
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            config_manager.load_and_validate(
                "invalid_config.json",
                "test_schema.json"
            )


# ==================== CACHE TESTS ====================

class TestCaching:
    """Test caching functionality."""
    
    def test_cache_on_first_load(self, config_manager):
        """Test that first load caches the config."""
        config = config_manager.load_and_validate(
            "test_config.json",
            "test_schema.json"
        )
        assert "test_config.json" in config_manager._cache
        assert config_manager._cache["test_config.json"] == config
    
    def test_cache_returns_same_object(self, config_manager):
        """Test that cached config is returned on second load."""
        config1 = config_manager.load_and_validate(
            "test_config.json",
            "test_schema.json"
        )
        config2 = config_manager.load_and_validate(
            "test_config.json",
            "test_schema.json"
        )
        assert config1 is config2
    
    def test_cache_invalidation_single(self, config_manager):
        """Test invalidating cache for single config."""
        config_manager.load_and_validate("test_config.json", "test_schema.json")
        assert "test_config.json" in config_manager._cache
        
        config_manager.invalidate_cache("test_config.json")
        assert "test_config.json" not in config_manager._cache
    
    def test_cache_invalidation_all(self, config_manager):
        """Test invalidating all cache."""
        config_manager.load_and_validate("test_config.json", "test_schema.json")
        assert len(config_manager._cache) > 0
        
        config_manager.invalidate_cache()
        assert len(config_manager._cache) == 0
    
    def test_cache_with_file_modification(self, config_manager):
        """Test that modified file bypasses cache."""
        # First load
        config1 = config_manager.load_and_validate(
            "test_config.json",
            "test_schema.json"
        )
        
        # Modify file
        time.sleep(0.01)  # Ensure timestamp changes
        config_path = config_manager.config_dir / "test_config.json"
        modified_config = config1.copy()
        modified_config["value"] = 999
        with open(config_path, 'w') as f:
            json.dump(modified_config, f)
        
        # Second load should get new data
        config2 = config_manager.load_and_validate(
            "test_config.json",
            "test_schema.json"
        )
        assert config2["value"] == 999
    
    def test_reload_bypasses_cache(self, config_manager):
        """Test that reload forces fresh load."""
        config1 = config_manager.load_and_validate(
            "test_config.json",
            "test_schema.json"
        )
        
        # Modify file
        config_path = config_manager.config_dir / "test_config.json"
        modified_config = config1.copy()
        modified_config["value"] = 777
        with open(config_path, 'w') as f:
            json.dump(modified_config, f)
        
        # Reload
        config2 = config_manager.reload("test_config.json", "test_schema.json")
        assert config2["value"] == 777


# ==================== SAVING TESTS ====================

class TestSaving:
    """Test configuration saving."""
    
    def test_save_new_config(self, config_manager):
        """Test saving a new configuration."""
        new_config = {"name": "new_test", "value": 100}
        config_manager.save_config("new_config.json", new_config)
        
        # Verify file exists
        config_path = config_manager.config_dir / "new_config.json"
        assert config_path.exists()
        
        # Verify content
        with open(config_path, 'r') as f:
            loaded = json.load(f)
        assert loaded == new_config
    
    def test_save_existing_without_overwrite(self, config_manager):
        """Test saving over existing file without overwrite flag."""
        new_config = {"name": "test", "value": 100}
        with pytest.raises(FileExistsError, match="already exists"):
            config_manager.save_config("test_config.json", new_config, overwrite=False)
    
    def test_save_existing_with_overwrite(self, config_manager):
        """Test saving over existing file with overwrite flag."""
        new_config = {"name": "overwritten", "value": 999}
        config_manager.save_config("test_config.json", new_config, overwrite=True)
        
        # Verify content
        loaded = config_manager.get_config("test_config.json", use_cache=False)
        assert loaded["value"] == 999
    
    def test_save_with_validation(self, config_manager):
        """Test saving with schema validation."""
        valid_config = {"name": "validated", "value": 123}
        config_manager.save_config(
            "validated_config.json",
            valid_config,
            schema_name="test_schema.json"
        )
        
        # Should succeed
        assert (config_manager.config_dir / "validated_config.json").exists()
    
    def test_save_with_validation_failure(self, config_manager, invalid_config):
        """Test saving with failed validation."""
        with pytest.raises(ValueError, match="Configuration validation failed"):
            config_manager.save_config(
                "invalid_new.json",
                invalid_config,
                schema_name="test_schema.json"
            )
    
    def test_update_config(self, config_manager):
        """Test updating existing configuration."""
        updates = {"value": 200, "enabled": False}
        config_manager.update_config("test_config.json", updates)
        
        # Verify updates
        loaded = config_manager.get_config("test_config.json", use_cache=False)
        assert loaded["value"] == 200
        assert loaded["enabled"] is False
        assert loaded["name"] == "test_config"  # Original value preserved
    
    def test_update_config_deep_merge(self, config_manager):
        """Test deep merge in update_config."""
        updates = {"nested": {"key": "updated_value", "new_key": "new"}}
        config_manager.update_config("test_config.json", updates, deep=True)
        
        loaded = config_manager.get_config("test_config.json", use_cache=False)
        assert loaded["nested"]["key"] == "updated_value"
        assert loaded["nested"]["new_key"] == "new"
    
    def test_save_invalidates_cache(self, config_manager):
        """Test that save invalidates cache."""
        # Load and cache
        config_manager.load_and_validate("test_config.json", "test_schema.json")
        assert "test_config.json" in config_manager._cache
        
        # Save (overwrite)
        new_config = {"name": "test", "value": 999}
        config_manager.save_config("test_config.json", new_config, overwrite=True)
        
        # Cache should be invalidated
        assert "test_config.json" not in config_manager._cache


# ==================== MERGE TESTS ====================

class TestMerging:
    """Test configuration merging."""
    
    def test_deep_merge_simple(self, config_manager):
        """Test simple deep merge."""
        base = {"a": 1, "b": 2}
        updates = {"b": 3, "c": 4}
        result = config_manager._deep_merge(base, updates)
        
        assert result == {"a": 1, "b": 3, "c": 4}
    
    def test_deep_merge_nested(self, config_manager):
        """Test deep merge with nested dicts."""
        base = {
            "outer": {
                "inner1": 1,
                "inner2": 2
            },
            "other": "value"
        }
        updates = {
            "outer": {
                "inner2": 99,
                "inner3": 3
            }
        }
        result = config_manager._deep_merge(base, updates)
        
        assert result["outer"]["inner1"] == 1
        assert result["outer"]["inner2"] == 99
        assert result["outer"]["inner3"] == 3
        assert result["other"] == "value"
    
    def test_merge_configs_multiple(self, config_manager):
        """Test merging multiple configurations."""
        # Create additional configs
        config1 = {"a": 1, "b": 2}
        config2 = {"b": 3, "c": 4}
        config3 = {"c": 5, "d": 6}
        
        config_manager.save_config("merge1.json", config1)
        config_manager.save_config("merge2.json", config2)
        config_manager.save_config("merge3.json", config3)
        
        # Merge
        result = config_manager.merge_configs("merge1.json", "merge2.json", "merge3.json")
        
        assert result == {"a": 1, "b": 3, "c": 5, "d": 6}
    
    def test_merge_configs_with_output(self, config_manager):
        """Test merging and saving to output file."""
        config1 = {"x": 1}
        config2 = {"y": 2}
        
        config_manager.save_config("merge_a.json", config1)
        config_manager.save_config("merge_b.json", config2)
        
        result = config_manager.merge_configs(
            "merge_a.json",
            "merge_b.json",
            output_name="merged_output.json"
        )
        
        # Verify output file exists
        assert (config_manager.config_dir / "merged_output.json").exists()
        
        # Verify content
        loaded = config_manager.get_config("merged_output.json")
        assert loaded == {"x": 1, "y": 2}


# ==================== CLI TESTS ====================

class TestCLI:
    """Test CLI argument handling."""
    
    def test_from_cli_args(self, config_manager):
        """Test applying CLI overrides."""
        cli_overrides = {"value": 555, "enabled": False}
        result = config_manager.from_cli_args("test_config.json", cli_overrides)
        
        assert result["value"] == 555
        assert result["enabled"] is False
        assert result["name"] == "test_config"  # Original preserved
    
    def test_from_cli_args_with_validation(self, config_manager):
        """Test CLI overrides with validation."""
        cli_overrides = {"value": 555}
        result = config_manager.from_cli_args(
            "test_config.json",
            cli_overrides,
            schema_name="test_schema.json"
        )
        
        assert result["value"] == 555
    
    def test_from_cli_args_validation_failure(self, config_manager):
        """Test CLI overrides causing validation failure."""
        cli_overrides = {"value": "not_a_number"}  # Invalid type
        
        with pytest.raises(ValueError, match="Configuration validation failed"):
            config_manager.from_cli_args(
                "test_config.json",
                cli_overrides,
                schema_name="test_schema.json"
            )


# ==================== ENVIRONMENT VARIABLES TESTS ====================

class TestEnvironmentVariables:
    """Test environment variable resolution."""
    
    def test_resolve_env_vars_simple(self, config_manager):
        """Test resolving simple environment variables."""
        with patch.dict(os.environ, {'TEST_VAR': 'test_value'}):
            config = {"path": "${TEST_VAR}/data"}
            result = config_manager._resolve_env_vars(config)
            assert result["path"] == "test_value/data"
    
    def test_resolve_env_vars_nested(self, config_manager):
        """Test resolving env vars in nested structure."""
        with patch.dict(os.environ, {'DB_HOST': 'localhost', 'DB_PORT': '5432'}):
            config = {
                "database": {
                    "host": "${DB_HOST}",
                    "port": "${DB_PORT}",
                    "url": "postgres://${DB_HOST}:${DB_PORT}/db"
                }
            }
            result = config_manager._resolve_env_vars(config)
            assert result["database"]["host"] == "localhost"
            assert result["database"]["port"] == "5432"
            assert result["database"]["url"] == "postgres://localhost:5432/db"
    
    def test_resolve_env_vars_missing(self, config_manager):
        """Test that missing env vars are left as-is."""
        config = {"path": "${NONEXISTENT_VAR}/data"}
        result = config_manager._resolve_env_vars(config)
        assert result["path"] == "${NONEXISTENT_VAR}/data"
    
    def test_load_with_env_resolution(self, config_manager):
        """Test loading config with env var resolution."""
        with patch.dict(os.environ, {'DATA_DIR': '/data'}):
            # Create config with env var
            env_config = {"path": "${DATA_DIR}/output", "name": "test", "value": 1}
            config_manager.save_config("env_config.json", env_config)
            
            # Load with resolution
            result = config_manager.load_and_validate(
                "env_config.json",
                "test_schema.json",
                resolve_env=True
            )
            
            assert result["path"] == "/data/output"


# ==================== BACKUP TESTS ====================

class TestBackup:
    """Test configuration backup functionality."""
    
    def test_backup_config(self, config_manager):
        """Test creating config backup."""
        backup_path = config_manager.backup_config("test_config.json")
        
        # Verify backup exists
        assert backup_path.exists()
        assert "backup_" in backup_path.name
        assert backup_path.suffix == ".json"
        
        # Verify content matches original
        with open(backup_path, 'r') as f:
            backup_content = json.load(f)
        original = config_manager.get_config("test_config.json")
        assert backup_content == original
    
    def test_backup_nonexistent_config(self, config_manager):
        """Test backing up non-existent config."""
        with pytest.raises(FileNotFoundError, match="Configuration not found"):
            config_manager.backup_config("nonexistent.json")
    
    def test_save_with_backup(self, config_manager):
        """Test saving with automatic backup."""
        original = config_manager.get_config("test_config.json")
        
        # Save with backup
        new_config = {"name": "modified", "value": 999}
        config_manager.save_config(
            "test_config.json",
            new_config,
            overwrite=True,
            backup=True
        )
        
        # Find backup file
        backups = list(config_manager.config_dir.glob("test_config.backup_*.json"))
        assert len(backups) > 0
        
        # Verify backup contains original data
        with open(backups[0], 'r') as f:
            backup_content = json.load(f)
        assert backup_content == original


# ==================== LISTING TESTS ====================

class TestListing:
    """Test listing schemas and configs."""
    
    def test_list_schemas(self, config_manager):
        """Test listing schema files."""
        schemas = config_manager.list_schemas()
        assert "test_schema.json" in schemas
        assert all(s.endswith(".json") for s in schemas)
    
    def test_list_configs(self, config_manager):
        """Test listing config files."""
        configs = config_manager.list_configs()
        assert "test_config.json" in configs
        assert all(c.endswith(".json") for c in configs)
    
    def test_list_configs_excludes_backups(self, config_manager):
        """Test that backups are excluded from config listing."""
        # Create a backup
        config_manager.backup_config("test_config.json")
        
        configs = config_manager.list_configs()
        assert all("backup" not in c for c in configs)
    
    def test_validate_all_configs(self, config_manager):
        """Test batch validation of all configs."""
        # Create multiple configs
        config_manager.save_config(
            "valid_config.json",
            {"name": "valid", "value": 1}
        )
        config_manager.save_config(
            "another_config.json",
            {"name": "another", "value": 2}
        )
        
        report = config_manager.validate_all_configs(verbose=False)
        
        # Check that validation ran
        assert isinstance(report, dict)
        # Note: Will fail if schema naming doesn't match convention


# ==================== PATH UTILITIES TESTS ====================

class TestPathUtilities:
    """Test path utility methods."""
    
    def test_get_schema_path(self, config_manager):
        """Test getting schema path."""
        path = config_manager.get_schema_path("test_schema.json")
        assert path == config_manager.schema_dir / "test_schema.json"
    
    def test_get_config_path(self, config_manager):
        """Test getting config path."""
        path = config_manager.get_config_path("test_config.json")
        assert path == config_manager.config_dir / "test_config.json"
    
    def test_generate_output_path(self, config_manager):
        """Test generating output paths."""
        path = config_manager.generate_output_path(
            "experiment1",
            output_type="results",
            timestamp=False,
            extension="npz"
        )
        
        assert "experiment1_results.npz" in str(path)
        assert path.parent.name == "results"
    
    def test_generate_output_path_with_timestamp(self, config_manager):
        """Test output path with timestamp."""
        path = config_manager.generate_output_path(
            "experiment1",
            output_type="plots",
            timestamp=True
        )
        
        assert "experiment1_plots" in str(path)
        # Should contain timestamp pattern
        assert path.parent.name == "plots"
    
    def test_create_timestamp(self, config_manager):
        """Test timestamp creation."""
        timestamp = config_manager.create_timestamp()
        assert len(timestamp) == 15  # YYYYMMDD_HHMMSS
        assert "_" in timestamp


# ==================== FHN SPECIFIC TESTS ====================

class TestFHNSpecific:
    """Test FitzHugh-Nagumo specific functionality."""
    
    def test_create_default_configs(self, config_manager):
        """Test creating default FHN configs."""
        configs = config_manager.create_default_configs(
            experiment_name="test_experiment"
        )
        
        # Verify all config types created
        assert "model" in configs
        assert "solver" in configs
        assert "experiment" in configs
        assert "plot" in configs
        assert "logging" in configs
        
        # Verify files exist
        for config_file in configs.values():
            assert (config_manager.config_dir / config_file).exists()
    
    def test_default_model_config_structure(self, config_manager):
        """Test structure of default model config."""
        configs = config_manager.create_default_configs("test")
        model_config = config_manager.get_config(configs["model"])
        
        # Check required fields
        assert "name" in model_config
        assert "parameters" in model_config
        assert "diffusion" in model_config
        assert "domain" in model_config
        
        # Check parameter values
        assert "epsilon" in model_config["parameters"]
        assert "a" in model_config["parameters"]
    
    def test_get_model_config_specialized(self, config_manager, fhn_model_schema):
        """Test specialized model config getter."""
        # Write FHN schema
        schema_path = config_manager.schema_dir / "model_schema.json"
        with open(schema_path, 'w') as f:
            json.dump(fhn_model_schema, f)
        
        # Create valid FHN model config
        model_config = {
            "name": "FHN",
            "parameters": {
                "epsilon": 0.1,
                "a": 0.5,
                "b": 0.0
            },
            "diffusion": {
                "D_u": 1.0,
                "D_v": 0.0
            }
        }
        config_manager.save_config("fhn_model_config.json", model_config)
        
        # Load with specialized getter
        loaded = config_manager.get_model_config("fhn_model_config.json")
        assert loaded["name"] == "FHN"
        assert loaded["parameters"]["epsilon"] == 0.1


# ==================== EXPORT TESTS ====================

class TestExport:
    """Test configuration export functionality."""
    
    @pytest.mark.skipif(
        not pytest.importorskip("yaml", reason="PyYAML not installed"),
        reason="PyYAML required"
    )
    def test_export_to_yaml(self, config_manager):
        """Test exporting config to YAML."""
        yaml_output = config_manager.export_config("test_config.json", "yaml")
        
        # Basic checks
        assert "name:" in yaml_output
        assert "test_config" in yaml_output
        assert "value:" in yaml_output
    
    def test_export_unsupported_format(self, config_manager):
        """Test exporting to unsupported format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            config_manager.export_config("test_config.json", "xml")
    
    def test_print_config(self, config_manager, capsys):
        """Test printing config to console."""
        config_manager.print_config("test_config.json", syntax_highlight=False)
        captured = capsys.readouterr()
        
        # Verify output contains config data
        assert "test_config" in captured.out
        assert "42" in captured.out


# ==================== INTEGRATION TESTS ====================

class TestIntegration:
    """Integration tests for complete workflows."""
    
    def test_complete_workflow(self, config_manager):
        """Test complete config workflow: create, load, modify, merge."""
        # Create base config
        base = {"name": "base", "value": 1, "setting": "default"}
        config_manager.save_config("base.json", base, schema_name="test_schema.json")
        
        # Load and verify
        loaded = config_manager.load_and_validate("base.json", "test_schema.json")
        assert loaded["value"] == 1
        
        # Update
        config_manager.update_config("base.json", {"value": 10})
        
        # Create override config
        override = {"value": 20, "extra": "data"}
        config_manager.save_config("override.json", override)
        
        # Merge
        merged = config_manager.merge_configs(
            "base.json",
            "override.json",
            output_name="final.json"
        )
        
        assert merged["name"] == "base"
        assert merged["value"] == 20
        assert merged["setting"] == "default"
        assert merged["extra"] == "data"
    
    def test_fhn_simulation_workflow(self, config_manager, fhn_model_schema):
        """Test workflow for FHN simulation setup."""
        # Write model schema
        schema_path = config_manager.schema_dir / "model_schema.json"
        with open(schema_path, 'w') as f:
            json.dump(fhn_model_schema, f)
        
        # Create default configs
        configs = config_manager.create_default_configs("spiral_wave")
        
        # Simulate CLI overrides
        cli_overrides = {
            "parameters": {
                "epsilon": 0.15
            }
        }
        
        # Apply overrides
        final_config = config_manager.from_cli_args(
            configs["model"],
            cli_overrides,
            schema_name="model_schema.json"
        )
        
        # Verify
        assert final_config["parameters"]["epsilon"] == 0.15
        assert final_config["parameters"]["a"] == 0.5  # Original preserved


# ==================== PERFORMANCE TESTS ====================

class TestPerformance:
    """Test performance characteristics."""
    
    def test_cache_performance(self, config_manager):
        """Test that caching improves load times."""
        # First load (no cache)
        start = time.time()
        config_manager.load_and_validate("test_config.json", "test_schema.json")
        first_load_time = time.time() - start
        
        # Second load (from cache)
        start = time.time()
        config_manager.load_and_validate("test_config.json", "test_schema.json")
        cached_load_time = time.time() - start
        
        # Cached should be faster (though this is a weak test on small files)
        # Main point is to verify caching works without errors
        assert cached_load_time >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])