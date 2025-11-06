import json
import jsonschema
import os

from pathlib import Path
from typing import Dict, List, Any
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
            validate(instance=config_data, schema=schema_data)
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


    def save_config(self, config_name: str, data: Dict, overwrite: bool = False) -> None:
        """
        Save a configuration to a JSON file.
        
        Args:
            config_name (str): Name of the configuration file.
            data (dict): Configuration data to save.
            overwrite (bool): Whether to overwrite existing file (default: False).
        """

        path = os.path.join(self.config_dir, config_name)

        if os.path.exists(path) and not overwrite:
            raise FileExistsError(f"Configuration file '{config_name}' already exists.")
        
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)

    
    def update_config(self, config_name: str, updates: Dict) -> None:
        """
        Update existing configuration file with new key-value pairs.
        
        Args:
            config_name (str): Name of the configuration file.
            updates (dict): Dictionary of values to update.
        """

        data = self._load_config(config_name)
        data.update(updates)
        self.save_config(config_name, data, overwrite=True)


    def list_schemas(self) -> List[str]:
        """
        List all configuration schema files available in the schemas directory.
        
        Returns:
            list: List of config schemas file names.
        """

        return [ file for file in os.listdir(self.schema_dir) if file.endswith(".json") ]


    def list_configs(self) -> List[str]:
        """
        List all configuration files available in the config directory.
        
        Returns:
            list: List of config file names.
        """

        return [ file for file in os.listdir(self.config_dir) if file.endswith(".json") ]
    

    def get_config(self, config_name: str) -> Dict:
        """
        Return a loaded configuration dictionary without validation.
        
        Args:
            config_name (str): Configuration file name.
            
        Returns:
            dict: Loaded configuration.
        """

        return self._load_config(config_name)
    

    def get_experiment_config(self, filename: str) -> Dict[str, Any]:
        """
        Load and validate experiment configuration file.
        
        Args:
            filename (str): Path to the experiment configuration file.
            
        Returns:
            dict: Validated experiment configuration.
        """

        return self.load_and_validate(filename, "experiment_schema.json")
    

    def get_database_config(self, filename: str) -> Dict[str, Any]:
        """
        Load and validate database configuration file.
        
        Args:
            filename (str): Path to the database configuration file.
            
        Returns:
            dict: Validated database configuration.
        """

        return self.load_and_validate(filename, "database_schema.json")
    

    def get_logging_config(self, filename: str) -> Dict[str, Any]:
        """
        Load and validate logging configuration file.
        
        Args:
            filename (str): Path to the logging configuration file.
            
        Returns:
            dict: Validated logging configuration.
        """

        return self.load_and_validate(filename, "logging_schema.json")
    

    def get_model_config(self, filename: str) -> Dict[str, Any]:
        """
        Load and validate model configuration file.
        
        Args:
            filename (str): Path to the model configuration file.
        
        Returns:
            dict: Validated model configuration.
        """

        return self.load_and_validate(filename, "model_schema.json")
    

    def get_solver_config(self, filename: str) -> Dict[str, Any]:
        """
        Load and validate solver configuration file.

        Args:
            filename (str): Path to the solver configuration file.

        Returns:
            dict: Validated solver configuration.  
        """

        return self.load_and_validate(filename, "solver_schema.json")
    

    def get_plot_config(self, filename: str) -> Dict[str, Any]:
        """
        Load and validate plot configuration file.
        
        Args:   
            filename (str): Path to the plot configuration file.
            
        Returns:
            dict: Validated plot configuration.
        """

        return self.load_and_validate(filename, "plot_schema.json")


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