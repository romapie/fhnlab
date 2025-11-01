import json
import jsonschema

from pathlib import Path
from typing import Dict
from jsonschema import validate, ValidationError

class ConfigurationManager:
    """
    Manages configuration and schema files for the application.

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
            """
        
        self.schema_dir = Path(schema_dir)
        self.config_dir = Path(config_dir)

        # Validation of directories
        if not self.schema_dir.exists():
            raise FileNotFoundError(f"Schema directory not found: {self.schema_dir}")
        if not self.config_dir.exists():
            raise FileNotFoundError(f"Configuration directory not found: {self.config_dir}")


    def _load_schema(self, name: str) -> Dict:
        """
        Load a schema JSON file by name.
        
        Args:
            name (str): Schema file name (without path).
            
        Returns:
            dict: Parsed JSON schema.
        """

        schema_path = self.schema_dir / name

        if not schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {schema_path}")
        
        with open(schema_path, "r", encoding="utf-8") as file:
            return json.load(file)


    def _load_config(self, name: str) -> Dict:
        """
        Load a configuration JSON file by name.
        
        Args:
            name (str): Configuration file name (without path).
            
        Returns:
            dict (str): Parsed JSON configuration.
        """

        config_path = self.config_dir / name

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration not found: {config_path}")
        
        with open(config_path, "r", encoding="utf-8") as file:
            return json.load(file)


    def _validate_config(self, config_data: Dict, schema_data: Dict) -> bool:
        """
        Validate a configuration dictionary against a JSON schema.
        
        Args:
            config_data (dict): Loaded configuration JSON.
            schema_data (dict): Corresponding JSON schema.
            
        Returns:
            bool: True if validation passes, raises ValidationError otherwise.
        """

        try:
            validate(instance=config_data, schema=schema_data):
            return True
        except ValidationError as e:
            raise ValueError(f"Configuration validation failed: {e.message}\nPath: {list(e.path)}")


    def load_and_validate(self, config_name: str, schema_name: str) -> Dict:
        """
        Load and validate a configuration file against a given schema.
        
        Args:
            config_name (str): Configuration file name (e.g. 'experiment_config.json').
            schema_name (str): Schema file name (e.g. 'experiment_schema.json').
            
        Returns:
            dict: Validated configuration data.
        """

        config_data = self._load_config(config_name)
        schema_data = self._load_schema(schema_name)
        
        self._validate_config(config_data, schema_data)


    def save_config(self) -> None:
        pass


    def list_schemas(self) -> None:
        pass


    def list_configs(self) -> None:
        pass


    def create_timestamp(self) -> None:
        pass


    def auto_update_timestamp(self) -> None:
        pass


    def get_schema_path(self) -> None:
        pass


    def get_config_path(self) -> None:
        pass


    def log_event(self) -> None:
        pass


    def merge_configs(self) -> None:
        pass


    def export_to_database(self) -> None:
        pass


    def from_cli_args(self) -> None:
        pass
    


    def reload(self) -> None:
        pass


    def generate_general_output_path(self) -> None:
        pass


    def _add_defaults(self) -> None:
        pass