"""
Grid interaction substep for the solar energy simulation.
Handles the interaction between communities and the grid, including load management
and dynamic pricing.
"""
import numpy as np
from typing import Dict, Any, List, Tuple

def monitor_grid_status(grid_station: Dict[str, Any], 
                       communities: List[Dict[str, Any]]) -> Tuple[float, float]:
    """
    Monitor the current status of the grid station and connected communities.
    
    Args:
        grid_station: Grid station data dictionary
        communities: List of all community data dictionaries
        
    Returns:
        Tuple of (available_capacity, grid_stability)
    """
    # Calculate total load from connected communities
    total_load = 0.0
    
    # Extract grid station ID (handling both scalar and array cases)
    grid_id = grid_station['id']
    if isinstance(grid_id, (np.ndarray, list)):
        grid_id = grid_id[0]  # Take first element if it's an array
    
    for community in communities:
        # Extract community's grid station ID (handling both scalar and array cases)
        comm_grid_id = community['grid_station_id']
        if isinstance(comm_grid_id, (np.ndarray, list)):
            comm_grid_id = comm_grid_id[0]  # Take first element if it's an array
            
        if comm_grid_id == grid_id:
            # Get power balance (handle both scalar and array cases)
            power_balance = community['power_balance']
            if isinstance(power_balance, (np.ndarray, list)):
                power_balance = power_balance[0]  # Take first element if it's an array
                
            # Positive power balance means importing from grid
            total_load += max(0, float(power_balance))
    
    # Get max capacity (handle both scalar and array cases)
    max_capacity = grid_station['max_capacity']
    if isinstance(max_capacity, (np.ndarray, list)):
        max_capacity = max_capacity[0]  # Take first element if it's an array
    max_capacity = float(max_capacity)
    
    # Calculate available capacity (as fraction of max capacity)
    available_capacity = max(0, max_capacity - total_load)
    capacity_utilization = total_load / max_capacity if max_capacity > 0 else 0
    
    # Grid stability (0-1) based on capacity utilization
    # 0.8 utilization is optimal, stability decreases as we approach 1.0
    grid_stability = 1.0 - min(max((capacity_utilization - 0.8) * 5, 0), 0.5)
    
    return float(available_capacity), float(grid_stability)

def update_grid_pricing(grid_station: Dict[str, Any],
                       available_capacity: float,
                       grid_stability: float,
                       base_grid_price: float) -> float:
    """
    Update grid pricing based on current conditions.
    
    Args:
        grid_station: Grid station data dictionary
        available_capacity: Available capacity in kW
        grid_stability: Current grid stability (0-1)
        base_grid_price: Base price for grid electricity ($/kWh)
        
    Returns:
        New dynamic price ($/kWh)
    """
    # Get max capacity (handle both scalar and array cases)
    max_capacity = grid_station['max_capacity']
    if isinstance(max_capacity, (np.ndarray, list)):
        max_capacity = max_capacity[0]  # Take first element if it's an array
    max_capacity = float(max_capacity)
    
    # Get reliability (handle both scalar and array cases)
    reliability = grid_station.get('reliability', 0.95)  # Default to 95% reliable
    if isinstance(reliability, (np.ndarray, list)):
        reliability = reliability[0]  # Take first element if it's an array
    reliability = float(reliability)
    
    # Base price adjustment based on available capacity
    # Lower capacity -> higher price
    capacity_factor = 1.0
    if max_capacity > 0:
        capacity_utilization = 1.0 - (available_capacity / max_capacity)
        capacity_factor = 1.0 + (capacity_utilization ** 2)  # Quadratic increase with utilization
    
    # Adjust price based on grid stability
    stability_factor = 1.0 / max(0.1, grid_stability)  # Higher stability -> lower price
    
    # Reliability adjustment
    reliability_factor = 1.0 + (1.0 - reliability)  # Less reliable -> higher price
    
    # Calculate dynamic price with bounds
    min_price = base_grid_price * 0.5
    max_price = base_grid_price * 2.0
    dynamic_price = base_grid_price * capacity_factor * stability_factor * reliability_factor
    
    return float(np.clip(dynamic_price, min_price, max_price))

def update_grid_state(grid_station: Dict[str, Any],
                     dynamic_price: float,
                     communities: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Update the grid station state with new pricing and load information.
    
    Args:
        grid_station: Grid station data dictionary
        dynamic_price: New dynamic price ($/kWh)
        communities: List of all community data dictionaries
        
    Returns:
        Updated grid station data
    """
    # Get grid station ID (handle both scalar and array cases)
    grid_id = grid_station['id']
    if isinstance(grid_id, (np.ndarray, list)):
        grid_id = grid_id[0]
    
    # Update the grid station's dynamic price
    grid_station['current_price'] = dynamic_price
    
    # Calculate total load and revenue from connected communities
    total_load = 0.0
    total_revenue = 0.0
    
    for community in communities:
        # Get community's grid station ID (handle both scalar and array cases)
        comm_grid_id = community['grid_station_id']
        if isinstance(comm_grid_id, (np.ndarray, list)):
            comm_grid_id = comm_grid_id[0]
            
        if comm_grid_id == grid_id:
            # Get power balance (handle both scalar and array cases)
            power_balance = community['power_balance']
            if isinstance(power_balance, (np.ndarray, list)):
                power_balance = power_balance[0]
            
            # Community is importing from grid (positive power balance)
            import_kwh = max(0, float(power_balance))
            total_load += import_kwh
            total_revenue += import_kwh * dynamic_price
            
            # Community is exporting to grid (negative power balance, but we pay less)
            export_kwh = abs(min(0, float(power_balance)))
            total_load -= export_kwh * 0.8  # We pay 80% of market price for exports
            total_revenue -= export_kwh * dynamic_price * 0.8
    
    # Get max capacity (handle both scalar and array cases)
    max_capacity = grid_station['max_capacity']
    if isinstance(max_capacity, (np.ndarray, list)):
        max_capacity = max_capacity[0]
    max_capacity = float(max_capacity)
    
    # Update grid station metrics
    grid_station['current_load'] = total_load
    grid_station['revenue'] = grid_station.get('revenue', 0.0) + total_revenue
    grid_station['total_energy_traded'] = grid_station.get('total_energy_traded', 0.0) + abs(total_load)
    
    # Initialize reliability if not exists
    if 'reliability' not in grid_station:
        grid_station['reliability'] = 0.95  # Default to 95% reliable
    
    # Update reliability based on load factor
    load_factor = total_load / max_capacity if max_capacity > 0 else 0
    if load_factor > 0.9:
        # Reduce reliability if operating near capacity
        grid_station['reliability'] = max(0.7, float(grid_station['reliability']) - 0.02)
    else:
        # Gradually recover reliability
        grid_station['reliability'] = min(0.95, float(grid_station['reliability']) + 0.01)
    
    # Ensure reliability is a float
    grid_station['reliability'] = float(grid_station['reliability'])
    
    return grid_station

def process_grid_station(grid_station: Dict[str, Any],
                        communities: List[Dict[str, Any]],
                        base_grid_price: float) -> Dict[str, Any]:
    """
    Process a single grid station's state update.
    
    Args:
        grid_station: Grid station data dictionary
        communities: List of all community data dictionaries
        base_grid_price: Base price for grid electricity ($/kWh)
        
    Returns:
        Updated grid station data
    """
    # Handle case where grid_station is a single element in a list
    if isinstance(grid_station, list) and len(grid_station) == 1:
        grid_station = grid_station[0]
    
    # Make a copy to avoid modifying the original
    grid_station = dict(grid_station)
    
    # Monitor current status
    available_capacity, grid_stability = monitor_grid_status(grid_station, communities)
    
    # Update pricing based on current conditions
    dynamic_price = update_grid_pricing(
        grid_station,
        available_capacity,
        grid_stability,
        base_grid_price
    )
    
    # Update grid station state with new pricing and load information
    updated_grid = update_grid_state(
        grid_station,
        dynamic_price,
        communities
    )
    
    # Ensure all values are native Python types (not numpy types)
    for key, value in updated_grid.items():
        if isinstance(value, (np.integer, np.floating)):
            updated_grid[key] = float(value)
        elif isinstance(value, np.ndarray) and value.size == 1:
            updated_grid[key] = float(value[0])
    
    return updated_grid
