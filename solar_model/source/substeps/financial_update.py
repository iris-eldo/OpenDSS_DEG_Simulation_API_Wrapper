"""
Financial update substep for the solar energy simulation.
Handles the calculation and updating of financial metrics for households.
"""
import numpy as np
from typing import Dict, Any, List, Tuple

def calculate_monthly_financials(household: Dict[str, Any],
                               community: Dict[str, Any],
                               grid_buy_price: float,
                               grid_sell_ratio: float) -> Dict[str, float]:
    """
    Calculate monthly financial metrics for a household.
    
    Args:
        household: Household data dictionary
        community: Community data dictionary
        grid_buy_price: Price to buy from grid ($/kWh)
        grid_sell_ratio: Ratio of buy price for selling to grid
        
    Returns:
        Dictionary of financial metrics
    """
    # Get current month (0-11 for array indexing)
    month_idx = (household.get('current_month', 1) - 1) % 12
    
    # Get monthly demand (kWh)
    monthly_demand = household['demand_profile'][month_idx]
    
    # Calculate costs without solar
    cost_without_solar = monthly_demand * grid_buy_price
    
    # Calculate actual costs with solar
    grid_consumption = household['grid_consumption']
    excess_energy = household['excess_energy']
    
    # Cost of buying from grid
    grid_cost = grid_consumption * grid_buy_price
    
    # Revenue from selling excess
    sell_price = grid_buy_price * grid_sell_ratio
    sell_revenue = excess_energy * sell_price
    
    # Net monthly cost with solar
    net_cost_with_solar = max(0, grid_cost - sell_revenue)
    
    # Monthly savings
    monthly_savings = cost_without_solar - net_cost_with_solar
    
    # Maintenance costs (annual cost divided by 12)
    maintenance_cost = 0.0
    if household['has_solar']:
        maintenance_cost = (household['generation_capacity'] * 1000 *  # kW to W
                          0.01) / 12  # $0.01/W/year -> monthly
    
    # Net savings after maintenance
    net_savings = monthly_savings - maintenance_cost
    
    return {
        'monthly_demand': monthly_demand,
        'cost_without_solar': cost_without_solar,
        'grid_consumption': grid_consumption,
        'excess_energy': excess_energy,
        'grid_cost': grid_cost,
        'sell_revenue': sell_revenue,
        'net_cost_with_solar': net_cost_with_solar,
        'monthly_savings': monthly_savings,
        'maintenance_cost': maintenance_cost,
        'net_savings': net_savings
    }

def update_household_finances(household: Dict[str, Any],
                             financials: Dict[str, float]) -> Dict[str, Any]:
    """
    Update household financial state.
    
    Args:
        household: Household data dictionary
        financials: Output from calculate_monthly_financials
        
    Returns:
        Updated household data
    """
    # Update savings
    household['monthly_savings'] = financials['net_savings']
    household['cumulative_savings'] += financials['net_savings']
    
    # Update ROI if they have solar
    if household['has_solar'] and household.get('installation_cost', 0) > 0:
        # Simple ROI: (total savings - installation cost) / installation cost * 100
        total_savings = household['cumulative_savings']
        installation_cost = household.get('installation_cost', 1)  # Avoid division by zero
        household['expected_roi'] = ((total_savings - installation_cost) / installation_cost) * 100
    
    return household

def update_roi_expectations(household: Dict[str, Any],
                           financials: Dict[str, float],
                           current_month: int) -> Dict[str, Any]:
    """
    Update ROI expectations based on actual performance.
    
    Args:
        household: Household data dictionary
        financials: Output from calculate_monthly_financials
        current_month: Current month (1-12)
        
    Returns:
        Updated household data with adjusted ROI expectations
    """
    if household['has_solar']:
        # If they have solar, update ROI based on actual performance
        if 'installation_cost' in household and household['installation_cost'] > 0:
            months_operating = (current_month - household.get('installation_month', current_month)) % 12
            months_operating = max(1, months_operating)  # Avoid division by zero
            
            # Project annual savings based on current month
            projected_annual_savings = financials['net_savings'] * (12 / months_operating)
            
            # Update expected ROI
            if household['installation_cost'] > 0:
                household['expected_roi'] = (projected_annual_savings / household['installation_cost']) * 100
    else:
        # If they don't have solar, adjust propensity based on observed savings
        if 'neighbor_adoption' in household and any(household['neighbor_adoption']):
            # Get average ROI of neighbors with solar
            neighbor_roi = [
                h['expected_roi'] 
                for i, h in enumerate(household['neighbor_adoption']) 
                if h and i < len(household['neighbor_adoption'])
            ]
            
            if neighbor_roi:
                avg_neighbor_roi = sum(neighbor_roi) / len(neighbor_roi)
                # Adjust adoption propensity based on neighbor ROI
                # Higher neighbor ROI increases propensity
                household['adoption_propensity'] = min(
                    household['adoption_propensity'] * (1 + (avg_neighbor_roi / 100)),
                    1.0  # Cap at 1.0
                )
    
    return household
