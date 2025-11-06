import json
import jsonschema
import os
import shutil
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from jsonschema import validate, ValidationError
from datetime import datetime


class ConfigurationManager:
    """
    Manages configuration and schema files for the fhnlab application.
    
    Handles loading, validation, caching, merging, and saving of JSON configurations
    for FitzHugh-Nagumo reaction-diffusion simulations.
    
    Attributes:
        schema_dir (Path): Path to the directory containing JSON schema files.
        config_dir (Path): Path to the directory containing configuration files.
    """
    
    def __init__(self, schema_dir: str, config_dir: str):
        """
        Initialize the ConfigurationManager with directories for schemas and configurations.
        
        Args:
            schema_dir (str): Path to the directory containing schema files.
            config_dir (str): Path to the directory containing configuration files.
            
        Raises:
            FileNotFoundError: If schema or config directory doesn't exist.
        """
        self.schema_dir = Path(schema_dir)
        self.config_dir = Path(config_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._timestamps: Dict[str, float] = {}
        
        # Validation of directories
        if not self.schema_dir.exists():
            raise FileNotFoundError(f"Schema directory not found: {self.schema_dir}")
        if not self.config_dir.exists():
            raise FileNotFoundError(f"Configuration directory not found: {self.config_dir}")
    
    # ==================== PRIVATE HELPER METHODS ====================
    
    def _load_schema(self, name: str) -> Dict[str, Any]:
        """
        Load a schema JSON file by name.
        
        Args:
            name (str): Schema file name (without path).
            
        Returns:
            Dict[str, Any]: Parsed JSON schema.
            
        Raises:
            FileNotFoundError: If schema file doesn't exist.
        """
        schema_path = self.schema_dir / name
        
        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {schema_path}")
        
        with open(schema_path, "r", encoding="utf-8") as file:
            return json.load(file)
    
    def _load_config(self, name: str) -> Dict[str, Any]:
        """
        Load a configuration JSON file by name.
        
        Args:
            name (str): Configuration file name (without path).
            
        Returns:
            Dict[str, Any]: Parsed JSON configuration.
            
        Raises:
            FileNotFoundError: If configuration file doesn't exist.
        """
        config_path = self.config_dir / name
        
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration not found: {config_path}")
        
        with open(config_path, "r", encoding="utf-8") as file:
            return json.load(file)
    
    def _validate_config(self, config_data: Dict[str, Any], schema_data: Dict[str, Any]) -> bool:
        """
        Validate a configuration dictionary against a JSON schema.
        
        Args:
            config_data (Dict[str, Any]): Loaded configuration JSON.
            schema_data (Dict[str, Any]): Corresponding JSON schema.
            
        Returns:
            bool: True if validation passes.
            
        Raises:
            ValueError: If validation fails with details about the error.
        """
        try:
            validate(instance=config_data, schema=schema_data)
            return True
        except ValidationError as e:
            raise ValueError(
                f"Configuration validation failed: {e.message}\n"
                f"Path: {list(e.path)}\n"
                f"Schema path: {list(e.schema_path)}"
            )
    
    def _deep_merge(self, base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries. Later values override earlier ones.
        
        Args:
            base (Dict[str, Any]): Base dictionary.
            updates (Dict[str, Any]): Updates to merge into base.
            
        Returns:
            Dict[str, Any]: Merged dictionary.
        """
        result = base.copy()
        for key, value in updates.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
    
    def _resolve_env_vars(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Resolve ${ENV_VAR} placeholders in config values recursively.
        
        Args:
            config (Dict[str, Any]): Configuration with potential env var placeholders.
            
        Returns:
            Dict[str, Any]: Configuration with resolved environment variables.
        """
        def resolve_value(value: Any) -> Any:
            if isinstance(value, str):
                pattern = r'\$\{([^}]+)\}'
                return re.sub(
                    pattern,
                    lambda m: os.getenv(m.group(1), m.group(0)),
                    value
                )
            elif isinstance(value, dict):
                return {k: resolve_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve_value(item) for item in value]
            return value
        
        return resolve_value(config)
    
    def _add_defaults(self, config: Dict[str, Any], defaults: Dict[str, Any]) -> Dict[str, Any]:
        """
        Add default values for missing keys in configuration.
        
        Args:
            config (Dict[str, Any]): User configuration.
            defaults (Dict[str, Any]): Default values.
            
        Returns:
            Dict[str, Any]: Configuration with defaults applied.
        """
        result = defaults.copy()
        result.update(config)
        return result
    
    # ==================== CORE LOADING METHODS ====================
    
    def load_and_validate(
        self,
        config_name: str,
        schema_name: str,
        use_cache: bool = True,
        resolve_env: bool = False
    ) -> Dict[str, Any]:
        """
        Load and validate a configuration file against a given schema.
        Uses cache if enabled and the file hasn't changed since last load.
        
        Args:
            config_name (str): Configuration file name (e.g. 'experiment_config.json').
            schema_name (str): Schema file name (e.g. 'experiment_schema.json').
            use_cache (bool): Whether to use cached version if available.
            resolve_env (bool): Whether to resolve environment variables.
            
        Returns:
            Dict[str, Any]: Validated configuration data.
            
        Raises:
            FileNotFoundError: If config or schema file doesn't exist.
            ValueError: If validation fails.
        """
        config_path = self.config_dir / config_name
        
        # Use cached version if file unchanged
        if use_cache and config_name in self._cache:
            if config_path.exists():
                current_mtime = config_path.stat().st_mtime
                if self._timestamps.get(config_name) == current_mtime:
                    return self._cache[config_name]
        
        # Load fresh data
        config_data = self._load_config(config_name)
        schema_data = self._load_schema(schema_name)
        
        # Validate
        self._validate_config(config_data, schema_data)
        
        # Resolve environment variables if requested
        if resolve_env:
            config_data = self._resolve_env_vars(config_data)
        
        # Update cache
        if use_cache:
            self._cache[config_name] = config_data
            self._timestamps[config_name] = config_path.stat().st_mtime
        
        return config_data
    
    def get_config(self, config_name: str, use_cache: bool = True) -> Dict[str, Any]:
        """
        Return a loaded configuration dictionary without validation.
        
        Args:
            config_name (str): Configuration file name.
            use_cache (bool): Whether to use cached version if available.
            
        Returns:
            Dict[str, Any]: Loaded configuration.
        """
        config_path = self.config_dir / config_name
        
        if use_cache and config_name in self._cache:
            if config_path.exists():
                current_mtime = config_path.stat().st_mtime
                if self._timestamps.get(config_name) == current_mtime:
                    return self._cache[config_name]
        
        config_data = self._load_config(config_name)
        
        if use_cache:
            self._cache[config_name] = config_data
            self._timestamps[config_name] = config_path.stat().st_mtime
        
        return config_data
    
    # ==================== SPECIALIZED GETTERS ====================
    
    def get_experiment_config(self, filename: str) -> Dict[str, Any]:
        """
        Load and validate experiment configuration file.
        
        Args:
            filename (str): Experiment configuration filename.
            
        Returns:
            Dict[str, Any]: Validated experiment configuration.
        """
        return self.load_and_validate(filename, "experiment_schema.json")
    
    def get_database_config(self, filename: str) -> Dict[str, Any]:
        """
        Load and validate database configuration file.
        
        Args:
            filename (str): Database configuration filename.
            
        Returns:
            Dict[str, Any]: Validated database configuration.
        """
        return self.load_and_validate(filename, "database_schema.json")
    
    def get_logging_config(self, filename: str) -> Dict[str, Any]:
        """
        Load and validate logging configuration file.
        
        Args:
            filename (str): Logging configuration filename.
            
        Returns:
            Dict[str, Any]: Validated logging configuration.
        """
        return self.load_and_validate(filename, "logging_schema.json")
    
    def get_model_config(self, filename: str) -> Dict[str, Any]:
        """
        Load and validate FitzHugh-Nagumo model configuration file.
        
        Args:
            filename (str): Model configuration filename.
            
        Returns:
            Dict[str, Any]: Validated model configuration.
        """
        return self.load_and_validate(filename, "model_schema.json")
    
    def get_solver_config(self, filename: str) -> Dict[str, Any]:
        """
        Load and validate solver configuration file.
        
        Args:
            filename (str): Solver configuration filename.
            
        Returns:
            Dict[str, Any]: Validated solver configuration.
        """
        return self.load_and_validate(filename, "solver_schema.json")
    
    def get_plot_config(self, filename: str) -> Dict[str, Any]:
        """
        Load and validate plot configuration file.
        
        Args:
            filename (str): Plot configuration filename.
            
        Returns:
            Dict[str, Any]: Validated plot configuration.
        """
        return self.load_and_validate(filename, "plot_schema.json")
    
    # ==================== SAVING AND UPDATING ====================
    
    def save_config(
        self,
        config_name: str,
        data: Dict[str, Any],
        schema_name: Optional[str] = None,
        overwrite: bool = False,
        backup: bool = False
    ) -> None:
        """
        Save a configuration to a JSON file with optional validation.
        
        Args:
            config_name (str): Name of the configuration file.
            data (Dict[str, Any]): Configuration data to save.
            schema_name (Optional[str]): Schema to validate against before saving.
            overwrite (bool): Whether to overwrite existing file.
            backup (bool): Whether to create backup before overwriting.
            
        Raises:
            FileExistsError: If file exists and overwrite is False.
            ValueError: If validation fails.
        """
        config_path = self.config_dir / config_name
        
        # Check if file exists
        if config_path.exists() and not overwrite:
            raise FileExistsError(
                f"Configuration file '{config_name}' already exists. "
                f"Use overwrite=True to replace it."
            )
        
        # Create backup if requested and file exists
        if backup and config_path.exists():
            self.backup_config(config_name)
        
        # Validate before saving if schema provided
        if schema_name:
            schema_data = self._load_schema(schema_name)
            self._validate_config(data, schema_data)
        
        # Save to file
        with open(config_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
        
        # Invalidate cache for this config
        self.invalidate_cache(config_name)
    
    def update_config(
        self,
        config_name: str,
        updates: Dict[str, Any],
        deep: bool = True
    ) -> None:
        """
        Update existing configuration file with new key-value pairs.
        
        Args:
            config_name (str): Name of the configuration file.
            updates (Dict[str, Any]): Dictionary of values to update.
            deep (bool): Whether to perform deep merge for nested dicts.
        """
        data = self._load_config(config_name)
        
        if deep:
            data = self._deep_merge(data, updates)
        else:
            data.update(updates)
        
        self.save_config(config_name, data, overwrite=True)
    
    def backup_config(self, config_name: str) -> Path:
        """
        Create timestamped backup of configuration file.
        
        Args:
            config_name (str): Configuration file to backup.
            
        Returns:
            Path: Path to the backup file.
            
        Raises:
            FileNotFoundError: If config file doesn't exist.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{Path(config_name).stem}.backup_{timestamp}.json"
        
        src = self.config_dir / config_name
        dst = self.config_dir / backup_name
        
        if not src.exists():
            raise FileNotFoundError(f"Configuration not found: {src}")
        
        shutil.copy2(src, dst)
        return dst
    
    # ==================== MERGING AND CLI ====================
    
    def merge_configs(
        self,
        *config_names: str,
        output_name: Optional[str] = None,
        validate_with: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Merge multiple configurations with priority (later overrides earlier).
        
        Args:
            *config_names: Variable number of config file names to merge.
            output_name (Optional[str]): If provided, save merged config to this file.
            validate_with (Optional[str]): Schema to validate merged config against.
            
        Returns:
            Dict[str, Any]: Merged configuration.
        """
        result = {}
        for name in config_names:
            config = self._load_config(name)
            result = self._deep_merge(result, config)
        
        # Validate if schema provided
        if validate_with:
            schema_data = self._load_schema(validate_with)
            self._validate_config(result, schema_data)
        
        # Save if output name provided
        if output_name:
            self.save_config(output_name, result, overwrite=True)
        
        return result
    
    def from_cli_args(
        self,
        config_name: str,
        cli_overrides: Dict[str, Any],
        schema_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Load config and apply CLI argument overrides.
        
        Args:
            config_name (str): Base configuration file.
            cli_overrides (Dict[str, Any]): Overrides from CLI arguments.
            schema_name (Optional[str]): Schema to validate final config.
            
        Returns:
            Dict[str, Any]: Configuration with CLI overrides applied.
        """
        config = self._load_config(config_name)
        merged = self._deep_merge(config, cli_overrides)
        
        # Validate if schema provided
        if schema_name:
            schema_data = self._load_schema(schema_name)
            self._validate_config(merged, schema_data)
        
        return merged
    
    # ==================== CACHE MANAGEMENT ====================
    
    def invalidate_cache(self, config_name: Optional[str] = None) -> None:
        """
        Clear cache for specific config or all configs.
        
        Args:
            config_name (Optional[str]): Config to invalidate, or None for all.
        """
        if config_name:
            self._cache.pop(config_name, None)
            self._timestamps.pop(config_name, None)
        else:
            self._cache.clear()
            self._timestamps.clear()
    
    def reload(self, config_name: str, schema_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Force reload configuration from disk, bypassing cache.
        
        Args:
            config_name (str): Configuration file to reload.
            schema_name (Optional[str]): Schema to validate against.
            
        Returns:
            Dict[str, Any]: Reloaded configuration.
        """
        self.invalidate_cache(config_name)
        
        if schema_name:
            return self.load_and_validate(config_name, schema_name, use_cache=False)
        else:
            return self.get_config(config_name, use_cache=False)
    
    # ==================== LISTING AND VALIDATION ====================
    
    def list_schemas(self) -> List[str]:
        """
        List all configuration schema files available in the schemas directory.
        
        Returns:
            List[str]: List of schema file names.
        """
        return sorted([
            file.name for file in self.schema_dir.iterdir()
            if file.suffix == ".json"
        ])
    
    def list_configs(self) -> List[str]:
        """
        List all configuration files available in the config directory.
        
        Returns:
            List[str]: List of config file names.
        """
        return sorted([
            file.name for file in self.config_dir.iterdir()
            if file.suffix == ".json" and "backup" not in file.name
        ])
    
    def validate_all_configs(self, verbose: bool = True) -> Dict[str, bool]:
        """
        Validate all configs against their schemas and return report.
        
        Schema files are matched by replacing '_config.json' with '_schema.json'.
        
        Args:
            verbose (bool): Whether to print validation errors.
            
        Returns:
            Dict[str, bool]: Mapping of config names to validation success.
        """
        report = {}
        
        for config_file in self.list_configs():
            # Try to infer schema name from config name
            # e.g., "experiment_config.json" -> "experiment_schema.json"
            if "_config.json" in config_file:
                base_name = config_file.replace("_config.json", "")
                schema_file = f"{base_name}_schema.json"
            else:
                # Skip if we can't infer schema
                if verbose:
                    print(f"⚠️  {config_file}: Cannot infer schema name, skipping")
                continue
            
            try:
                self.load_and_validate(config_file, schema_file, use_cache=False)
                report[config_file] = True
                if verbose:
                    print(f"✅ {config_file}: Valid")
            except Exception as e:
                report[config_file] = False
                if verbose:
                    print(f"❌ {config_file}: {str(e)}")
        
        return report
    
    # ==================== OUTPUT AND DISPLAY ====================
    
    def print_config(
        self,
        config_name: str,
        syntax_highlight: bool = True,
        max_depth: Optional[int] = None
    ) -> None:
        """
        Pretty print configuration to console with optional syntax highlighting.
        
        Args:
            config_name (str): Configuration file to print.
            syntax_highlight (bool): Whether to use syntax highlighting.
            max_depth (Optional[int]): Maximum nesting depth to display.
        """
        config = self._load_config(config_name)
        json_str = json.dumps(config, indent=2, ensure_ascii=False)
        
        if syntax_highlight:
            try:
                from pygments import highlight
                from pygments.lexers import JsonLexer
                from pygments.formatters import TerminalFormatter
                
                print(highlight(json_str, JsonLexer(), TerminalFormatter()))
            except ImportError:
                print(json_str)
        else:
            print(json_str)
    
    def export_config(
        self,
        config_name: str,
        output_format: str = "yaml",
        output_path: Optional[str] = None
    ) -> str:
        """
        Export config to different formats (yaml, toml).
        
        Args:
            config_name (str): Configuration file to export.
            output_format (str): Target format ('yaml' or 'toml').
            output_path (Optional[str]): Path to save exported file.
            
        Returns:
            str: Exported configuration as string.
            
        Raises:
            ValueError: If output format is not supported.
        """
        config = self._load_config(config_name)
        
        if output_format.lower() == "yaml":
            try:
                import yaml
                output = yaml.dump(config, default_flow_style=False, allow_unicode=True)
            except ImportError:
                raise ImportError("PyYAML is required for YAML export. Install with: pip install pyyaml")
        
        elif output_format.lower() == "toml":
            try:
                import toml
                output = toml.dumps(config)
            except ImportError:
                raise ImportError("toml is required for TOML export. Install with: pip install toml")
        
        else:
            raise ValueError(f"Unsupported format: {output_format}. Use 'yaml' or 'toml'.")
        
        # Save to file if path provided
        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output)
        
        return output
    
    # ==================== PATH UTILITIES ====================
    
    def get_schema_path(self, schema_name: str) -> Path:
        """
        Get full path to a schema file.
        
        Args:
            schema_name (str): Schema file name.
            
        Returns:
            Path: Full path to schema file.
        """
        return self.schema_dir / schema_name
    
    def get_config_path(self, config_name: str) -> Path:
        """
        Get full path to a configuration file.
        
        Args:
            config_name (str): Configuration file name.
            
        Returns:
            Path: Full path to configuration file.
        """
        return self.config_dir / config_name
    
    def generate_output_path(
        self,
        experiment_name: str,
        output_type: str = "results",
        timestamp: bool = True,
        extension: str = "json"
    ) -> Path:
        """
        Generate standardized output path for experiment results.
        
        Args:
            experiment_name (str): Name of the experiment.
            output_type (str): Type of output (e.g., 'results', 'plots', 'logs').
            timestamp (bool): Whether to include timestamp in filename.
            extension (str): File extension.
            
        Returns:
            Path: Generated output path.
        """
        filename = f"{experiment_name}_{output_type}"
        
        if timestamp:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename}_{ts}"
        
        filename = f"{filename}.{extension}"
        
        # Create output directory if it doesn't exist
        output_dir = self.config_dir.parent / "output" / output_type
        output_dir.mkdir(parents=True, exist_ok=True)
        
        return output_dir / filename
    
    # ==================== DEFAULT CONFIGS FOR FHN ====================
    
    def create_default_configs(
        self,
        experiment_name: str = "default",
        overwrite: bool = False
    ) -> Dict[str, str]:
        """
        Create a complete set of default configs for FHN simulation.
        
        Args:
            experiment_name (str): Name for the experiment.
            overwrite (bool): Whether to overwrite existing configs.
            
        Returns:
            Dict[str, str]: Mapping of config type to filename.
        """
        configs = {}
        
        # Model configuration (FitzHugh-Nagumo parameters)
        model_config = {
            "name": "FitzHugh-Nagumo",
            "parameters": {
                "epsilon": 0.1,
                "a": 0.5,
                "b": 0.0,
                "I_ext": 0.0
            },
            "diffusion": {
                "D_u": 1.0,
                "D_v": 0.0,
                "anisotropic": False
            },
            "domain": {
                "Lx": 10.0,
                "Ly": 10.0,
                "nx": 128,
                "ny": 128
            }
        }
        model_file = f"{experiment_name}_model_config.json"
        self.save_config(model_file, model_config, overwrite=overwrite)
        configs["model"] = model_file
        
        # Solver configuration
        solver_config = {
            "method": "RK45",
            "time_span": [0.0, 100.0],
            "dt": 0.1,
            "rtol": 1e-6,
            "atol": 1e-8,
            "max_step": 1.0,
            "discretization": {
                "spatial_method": "finite_difference",
                "order": 2,
                "boundary_conditions": "periodic"
            }
        }
        solver_file = f"{experiment_name}_solver_config.json"
        self.save_config(solver_file, solver_config, overwrite=overwrite)
        configs["solver"] = solver_file
        
        # Experiment configuration
        experiment_config = {
            "name": experiment_name,
            "description": "FHN reaction-diffusion simulation",
            "initial_conditions": {
                "type": "spiral_wave",
                "amplitude": 1.0,
                "noise_level": 0.01
            },
            "heterogeneity": {
                "enabled": False,
                "type": "gaussian",
                "parameter": "epsilon",
                "mean": 0.0,
                "std": 0.02
            },
            "output": {
                "save_interval": 10,
                "save_fields": ["u", "v"],
                "format": "npz"
            }
        }
        experiment_file = f"{experiment_name}_experiment_config.json"
        self.save_config(experiment_file, experiment_config, overwrite=overwrite)
        configs["experiment"] = experiment_file
        
        # Plot configuration
        plot_config = {
            "style": "seaborn",
            "figure_size": [10, 8],
            "dpi": 150,
            "colormap": "viridis",
            "animation": {
                "fps": 30,
                "bitrate": 1800
            },
            "save_formats": ["png", "pdf"]
        }
        plot_file = f"{experiment_name}_plot_config.json"
        self.save_config(plot_file, plot_config, overwrite=overwrite)
        configs["plot"] = plot_file
        
        # Logging configuration
        logging_config = {
            "level": "INFO",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "handlers": {
                "console": True,
                "file": True,
                "file_path": f"logs/{experiment_name}.log"
            }
        }
        logging_file = f"{experiment_name}_logging_config.json"
        self.save_config(logging_file, logging_config, overwrite=overwrite)
        configs["logging"] = logging_file
        
        return configs
    
    # ==================== UTILITY METHODS ====================
    
    def create_timestamp(self) -> str:
        """
        Create standardized timestamp string.
        
        Returns:
            str: Timestamp in format YYYYMMDD_HHMMSS.
        """
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def log_event(
        self,
        event_type: str,
        config_name: str,
        details: Optional[str] = None
    ) -> None:
        """
        Log configuration management events.
        
        Args:
            event_type (str): Type of event (e.g., 'load', 'save', 'validate').
            config_name (str): Configuration file involved.
            details (Optional[str]): Additional details about the event.
        """
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] {event_type.upper()}: {config_name}"
        if details:
            log_entry += f" - {details}"
        
        # Could be extended to write to actual log file
        print(log_entry)