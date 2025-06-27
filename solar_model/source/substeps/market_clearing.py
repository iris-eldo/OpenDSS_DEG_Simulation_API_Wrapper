"""
Market clearing substep for the solar energy simulation.
Handles the aggregation of energy supply and demand within communities
and calculates the market clearing price.
"""
import numpy as np
from typing import Dict, Any, Tuple, List

def aggregate_community_energy(community: Dict[str, Any], 
                             households: List[Dict[str, Any]]) -> Tuple[float, float]:
    """
    Aggregate energy supply and demand for a community.
    
    Args:
        community: Community data dictionary
        households: List of household data dictionaries in the community
        
    Returns:
        Tuple of (total_supply, total_demand) in kWh
    """
    total_supply = 0.0
    total_demand = 0.0
    
    for household in households:
        if household['community_id'] == community['id']:
            total_supply += household['excess_energy']
            total_demand += household['grid_consumption']
    
    return total_supply, total_demand

def clear_market(total_supply: float, 
                 total_demand: float,
                 grid_buy_price: float,
                 grid_sell_ratio: float) -> Tuple[float, float]:
    """
    Calculate market clearing price and power balance.
    
    Args:
        total_supply: Total energy supply in the community (kWh)
        total_demand: Total energy demand in the community (kWh)
        grid_buy_price: Price to buy from grid ($/kWh)
        grid_sell_ratio: Ratio of buy price for selling to grid
        
    Returns:
        Tuple of (market_price, power_balance)
    """
    # Default to grid prices if no local market
    if total_supply <= 0 or total_demand <= 0:
        return grid_buy_price, total_demand - total_supply
    
    # Calculate market clearing price (simplified)
    # Price is between grid sell price and grid buy price
    grid_sell_price = grid_buy_price * grid_sell_ratio
    
    # Simple linear price function based on supply/demand ratio
    supply_demand_ratio = min(max(total_supply / (total_demand + 1e-6), 0.1), 10.0)
    
    # Price decreases as supply increases relative to demand
    price_factor = 0.5 + 0.5 * (1.0 / (1.0 + np.log10(supply_demand_ratio)))
    market_price = grid_sell_price + (grid_buy_price - grid_sell_price) * price_factor
    
    # Calculate power balance (positive means net import from grid)
    power_balance = total_demand - total_supply
    
    return float(market_price), float(power_balance)

def update_community_state(community: Dict[str, Any], 
                         market_price: float,
                         power_balance: float,
                         total_generation: float,
                         total_consumption: float) -> Dict[str, Any]:
    """
    Update community state with market clearing results.
    
    Args:
        community: Community data dictionary
        market_price: Market clearing price ($/kWh)
        power_balance: Net power balance (kWh)
        total_generation: Total generation in community (kWh)
        total_consumption: Total consumption in community (kWh)
        
    Returns:
        Updated community data
    """
    community['market_price'] = market_price
    community['power_balance'] = power_balance
    community['total_generation'] = total_generation
    community['total_consumption'] = total_consumption
    
    return community

def process_community(community: Dict[str, Any], 
                     households: List[Dict[str, Any]],
                     grid_buy_price: float,
                     grid_sell_ratio: float) -> Dict[str, Any]:
    """
    Process a single community's market clearing.
    
    Args:
        community: Community data dictionary
        households: List of all household data dictionaries
        grid_buy_price: Price to buy from grid ($/kWh)
        grid_sell_ratio: Ratio of buy price for selling to grid
        
    Returns:
        Updated community data
    """
    # Get households in this community
    community_households = [h for h in households if h['community_id'] == community['id']]
    
    # Aggregate supply and demand
    total_supply, total_demand = aggregate_community_energy(community, community_households)
    
    # Clear the market
    market_price, power_balance = clear_market(
        total_supply, total_demand, grid_buy_price, grid_sell_ratio
    )
    
    # Update community state
    community = update_community_state(
        community,
        market_price,
        power_balance,
        total_supply,  # In this simple model, total_generation = total_supply
        total_demand   # And total_consumption = total_demand
    )
    
    return community
