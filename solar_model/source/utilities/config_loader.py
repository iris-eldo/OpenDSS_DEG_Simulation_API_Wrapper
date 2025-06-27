"""
Configuration loader for the solar energy simulation.
Handles loading and parsing of the YAML configuration file.
"""
import yaml
import os

def load_config(config_path):
    """
    Load and parse the YAML configuration file.
    
    Args:
        config_path (str): Path to the YAML configuration file
        
    Returns:
        dict: Parsed configuration
    """
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        return config
    except Exception as e:
        print(f"Error loading config file {config_path}: {e}")
        raise

def validate_config(config):
    """
    Validate the configuration dictionary.
    
    Args:
        config (dict): Configuration to validate
        
    Raises:
        ValueError: If configuration is invalid
    """
    required_sections = ['simulation', 'environment', 'agents', 'substeps']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required config section: {section}")
    
    # Validate simulation parameters
    sim = config['simulation']
    if 'steps' not in sim or not isinstance(sim['steps'], int) or sim['steps'] <= 0:
        raise ValueError("Invalid or missing 'steps' in simulation config")
    
    # Validate environment parameters
    env = config['environment']
    required_env = ['grid_buy_price', 'grid_sell_ratio', 'solar_installation_cost']
    for param in required_env:
        if param not in env or not isinstance(env[param], (int, float)) or env[param] < 0:
            raise ValueError(f"Invalid or missing '{param}' in environment config")
    
    # Validate agent definitions
    required_agents = ['household', 'community', 'grid_station']
    for agent in required_agents:
        if agent not in config['agents']:
            raise ValueError(f"Missing agent definition: {agent}")
    
    # TODO: Add more validation as needed
