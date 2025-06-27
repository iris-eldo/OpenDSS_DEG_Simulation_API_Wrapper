"""
Data loading and preprocessing utilities for the solar energy simulation.
Handles loading of household, community, and grid station data from CSV files.
"""
import os
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any

def load_household_data(config: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """
    Load and preprocess household data from CSV files.
    
    Args:
        config: Simulation configuration dictionary
        
    Returns:
        Dictionary containing household data arrays
    """
    data_dir = os.path.join('config', 'data', 'household')
    
    # Load demand profiles
    demand_profiles = np.loadtxt(os.path.join(data_dir, 'demand_profile.csv'), delimiter=',')
    num_households = len(demand_profiles)
    
    # Load other household attributes
    household_data = {
        'id': np.arange(1, num_households + 1),
        'location': np.column_stack((
            np.random.uniform(42.2, 42.4, num_households),  # Latitude
            np.random.uniform(-71.2, -70.9, num_households)  # Longitude
        )),
        'community_id': np.random.randint(1, 11, num_households),  # 10 communities
        'demand_profile': demand_profiles,
        'financial_capacity': np.random.uniform(0.1, 1.0, num_households),
        'generation_capacity': np.zeros(num_households),  # Will be set during adoption
        'battery_capacity': np.random.uniform(5.0, 20.0, num_households),  # kWh
        'battery_charge': np.zeros(num_households),
        'grid_consumption': np.zeros(num_households),
        'excess_energy': np.zeros(num_households),
        'has_solar': np.zeros(num_households, dtype=bool),
        'neighbor_adoption': np.random.choice(
            [True, False], 
            size=(num_households, 10),
            p=[0.1, 0.9]
        ),
        'adoption_propensity': np.random.uniform(0, 0.5, num_households),
        'expected_roi': np.zeros(num_households),
        'monthly_savings': np.zeros(num_households),
        'cumulative_savings': np.zeros(num_households)
    }
    
    return household_data

def load_community_data(config: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """
    Load and preprocess community data.
    
    Args:
        config: Simulation configuration dictionary
        
    Returns:
        Dictionary containing community data arrays
    """
    num_communities = 10  # Fixed number of communities
    
    # Create community data
    community_data = {
        'id': np.arange(1, num_communities + 1),
        'grid_station_id': np.tile(np.arange(1, 4), 4)[:num_communities],  # 3 grid stations
        'household_ids': [np.array([]) for _ in range(num_communities)],  # Will be populated
        'market_price': np.full(num_communities, config['environment']['grid_buy_price']),
        'power_balance': np.zeros(num_communities),
        'total_generation': np.zeros(num_communities),
        'total_consumption': np.zeros(num_communities)
    }
    
    return community_data

def load_grid_data(config: Dict[str, Any]) -> Dict[str, np.ndarray]:
    """
    Load and preprocess grid station data.
    
    Args:
        config: Simulation configuration dictionary
        
    Returns:
        Dictionary containing grid station data arrays
    """
    num_grid_stations = 3  # Fixed number of grid stations
    
    # Create grid station data
    grid_data = {
        'id': np.arange(1, num_grid_stations + 1),
        'max_capacity': np.array([50000, 75000, 100000]),  # kW
        'current_load': np.zeros(num_grid_stations),
        'dynamic_price': np.full(num_grid_stations, config['environment']['grid_buy_price']),
        'reliability': np.array([0.99, 0.98, 0.99]),
        'total_generation': np.zeros(num_grid_stations),
        'total_consumption': np.zeros(num_grid_stations),
        'revenue': np.zeros(num_grid_stations)
    }
    
    return grid_data

def assign_households_to_communities(household_data: Dict[str, np.ndarray], 
                                   community_data: Dict[str, np.ndarray]) -> None:
    """
    Assign households to communities.
    
    Args:
        household_data: Dictionary of household data
        community_data: Dictionary of community data
    """
    household_ids = household_data['id']
    community_ids = household_data['community_id']
    
    # Assign household IDs to their respective communities
    for i, comm_id in enumerate(community_data['id']):
        mask = (community_ids == comm_id)
        community_data['household_ids'][i] = household_ids[mask]

def load_all_data(config: Dict[str, Any]) -> Dict[str, Dict[str, np.ndarray]]:
    """
    Load all data and perform necessary preprocessing.
    
    Args:
        config: Simulation configuration dictionary
        
    Returns:
        Dictionary containing all data
    """
    # Load individual datasets
    household_data = load_household_data(config)
    community_data = load_community_data(config)
    grid_data = load_grid_data(config)
    
    # Link households to communities
    assign_households_to_communities(household_data, community_data)
    
    return {
        'household': household_data,
        'community': community_data,
        'grid_station': grid_data
    }
