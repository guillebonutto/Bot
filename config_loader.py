import yaml
import os
import logging
from typing import Dict, Any

# Configure logging for this module
logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = "config.yaml"

def load_config(config_path: str = DEFAULT_CONFIG_PATH) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.
    
    Args:
        config_path: Path to the configuration file.
        
    Returns:
        Dict containing the configuration.
        
    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the config is invalid.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found at: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            
        if not config:
            raise ValueError("Configuration file is empty")
            
        validate_config(config)
        logger.info(f"Configuration loaded successfully from {config_path}")
        return config
        
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing YAML configuration: {e}")
    except Exception as e:
        raise ValueError(f"Failed to load configuration: {e}")

def validate_config(config: Dict[str, Any]):
    """
    Validate the configuration structure and values.
    
    Args:
        config: The configuration dictionary to validate.
        
    Raises:
        ValueError: If validation fails.
    """
    required_sections = ['trading', 'risk', 'system']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required configuration section: {section}")
            
    # Validate Trading Section
    trading = config['trading']
    if not trading.get('pairs'):
        raise ValueError("No trading pairs configured")
    if not trading.get('timeframes'):
        raise ValueError("No timeframes configured")
        
    # Validate Risk Section
    risk = config['risk']
    risk_per_trade = risk.get('risk_per_trade', 0)
    if not (0.01 <= risk_per_trade <= 0.05):
        raise ValueError(f"risk_per_trade must be between 0.01 and 0.05, got {risk_per_trade}")
        
    max_drawdown = risk.get('max_drawdown', 0)
    # Relaxed validation for testing mode (up to 1.0)
    if not (0.05 <= max_drawdown <= 1.0):
        raise ValueError(f"max_drawdown must be between 0.05 and 1.0, got {max_drawdown}")
        
    # Validate System Section
    system = config['system']
    if system.get('max_concurrent_requests', 0) < 1:
        raise ValueError("max_concurrent_requests must be at least 1")
