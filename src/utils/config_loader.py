import yaml
import os
from pathlib import Path
from typing import Dict, Any

# Resolve the absolute path to the project root
BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = BASE_DIR / "config"

class ConfigLoader:
    """Utility class to load YAML configuration files safely."""

    @staticmethod
    def _load_yaml(filename: str) -> Dict[str, Any]:
        filepath = CONFIG_DIR / filename
        if not filepath.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
            
        with open(filepath, 'r', encoding='utf-8') as file:
            try:
                return yaml.safe_load(file) or {}
            except yaml.YAMLError as e:
                raise ValueError(f"Error parsing YAML file {filename}: {e}")

    @staticmethod
    def load_settings() -> Dict[str, Any]:
        """Load the global pipeline, LLM, and VectorDB settings."""
        return ConfigLoader._load_yaml("settings.yml")

    @staticmethod
    def load_sources() -> Dict[str, Any]:
        """Load the registry of AI news sources to scrape."""
        return ConfigLoader._load_yaml("sources.yml")

    @staticmethod
    def load_subscribers() -> Dict[str, Any]:
        """Load the email subscriber list and preferences."""
        return ConfigLoader._load_yaml("subscribers.yml")
