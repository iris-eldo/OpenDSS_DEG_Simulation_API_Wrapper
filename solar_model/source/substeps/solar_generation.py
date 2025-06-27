"""
Solar generation substep for the solar energy simulation.
Handles the calculation of solar energy generation and updates to the energy balance.
"""
import numpy as np
from typing import Dict, Any, Tuple

def calculate_solar_generation(household: Dict[str, Any], 
                             current_month: int) -> Tuple[float, float]:
    """
    Calculate solar energy generation for a household.
    
    Args:
        household: Household data dictionary
        current_month: Current month (1-12)
        
    Returns:
        Tuple of (hourly_generation, daily_generation) in kWh
    """
    if not household['has_solar'] or household['generation_capacity'] <= 0:
        return 0.0, 0.0
    
    # Get generation capacity in kW
    capacity = household['generation_capacity']
    
    # Monthly capacity factors (approximate for Boston area, 0-1 scale)
    # Source: NREL PVWatts Calculator
    monthly_factors = np.array([
        0.30,  # Jan
        0.35,  # Feb
        0.45,  # Mar
        0.50,  # Apr
        0.55,  # May
        0.60,  # Jun
        0.65,  # Jul
        0.60,  # Aug
        0.55,  # Sep
        0.45,  # Oct
        0.35,  # Nov
        0.30   # Dec
    ])
    
    # Calculate daily generation (kWh)
    daily_generation = capacity * monthly_factors[current_month - 1] * 24
    
    # Assume 8 hours of equivalent peak sun per day
    hourly_generation = daily_generation / 8
    
    return float(hourly_generation), float(daily_generation)

def update_energy_balance(household: Dict[str, Any], 
                        hourly_generation: float,
                        daily_generation: float) -> Dict[str, float]:
    """
    Update the energy balance for a household.
    
    Args:
        household: Household data dictionary
        hourly_generation: Hourly solar generation in kWh
        daily_generation: Daily solar generation in kWh
        
    Returns:
        Dictionary with updated energy values
    """
    # Get current demand for the month (assuming demand_profile is 12 months)
    month_idx = (household.get('current_month', 1) - 1) % 12
    demand = household['demand_profile'][month_idx]
    
    # Calculate net energy (generation - demand)
    net_energy = daily_generation - demand
    
    # Initialize return values
    battery_charge = household['battery_charge']
    excess_energy = 0.0
    grid_consumption = 0.0
    
    if net_energy > 0:
        # Excess energy after meeting demand
        # Try to store in battery first
        battery_capacity = household['battery_capacity']
        available_battery = battery_capacity - battery_charge
        
        if available_battery >= net_energy:
            # All excess can be stored in battery
            battery_charge += net_energy
        else:
            # Fill battery, rest is excess
            battery_charge = battery_capacity
            excess_energy = net_energy - available_battery
    else:
        # Not enough generation, use battery or grid
        energy_needed = -net_energy
        
        if battery_charge >= energy_needed:
            # Get all needed energy from battery
            battery_charge -= energy_needed
        else:
            # Use all battery, get rest from grid
            energy_needed -= battery_charge
            battery_charge = 0
            grid_consumption = energy_needed
    
    return {
        'battery_charge': float(battery_charge),
        'excess_energy': float(excess_energy),
        'grid_consumption': float(grid_consumption)
    }

def update_household_state(household: Dict[str, Any], 
                         updates: Dict[str, float]) -> Dict[str, Any]:
    """
    Update household state with new energy values.
    
    Args:
        household: Household data dictionary
        updates: Dictionary of updates to apply
        
    Returns:
        Updated household data
    """
    for key, value in updates.items():
        if key in household:
            household[key] = value
    return household
