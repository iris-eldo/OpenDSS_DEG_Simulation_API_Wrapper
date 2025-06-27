"""
Solar adoption substep for the solar energy simulation.
Handles the decision-making process for households adopting solar panels.
"""
import numpy as np
from typing import Dict, Any, List, Tuple

def evaluate_solar_potential(household: Dict[str, Any], 
                           current_month: int,
                           grid_price: float,
                           solar_installation_cost: float,
                           solar_maintenance_cost: float) -> Dict[str, float]:
    """
    Evaluate the potential for solar adoption for a household.
    
    Args:
        household: Household data dictionary
        current_month: Current month (1-12)
        grid_price: Current grid price ($/kWh)
        solar_installation_cost: Cost per watt installed ($/W)
        solar_maintenance_cost: Annual maintenance cost ($/W/year)
        
    Returns:
        Dictionary of adoption metrics
    """
    if household['has_solar']:
        return {
            'viable': False,
            'expected_roi': household['expected_roi']
        }
    
    # Calculate potential system size (kW) based on roof space and financial capacity
    # Assuming 15 sq.m per kW and 200 W panels (5 panels per kW)
    max_system_size = min(
        household['financial_capacity'] * 20,  # Up to 20 kW based on financial capacity
        10.0  # Maximum system size in kW
    )
    
    if max_system_size < 1.0:  # Minimum viable system size
        return {
            'viable': False,
            'expected_roi': 0.0
        }
    
    # Estimate annual energy production (kWh)
    # Using PVWatts-like calculation: system_size * solar_hours_per_day * 365 * performance_ratio
    # Boston average: ~4.5 sun hours per day, 0.75 performance ratio
    annual_production = max_system_size * 4.5 * 365 * 0.75
    
    # Estimate annual savings
    annual_savings = annual_production * grid_price
    
    # Calculate costs
    installation_cost = max_system_size * 1000 * solar_installation_cost  # Convert kW to W
    annual_maintenance = max_system_size * 1000 * solar_maintenance_cost
    
    # Simple ROI calculation (years to break even)
    # ROI = (annual savings - annual costs) / installation cost
    annual_net_savings = annual_savings - annual_maintenance
    roi_percentage = (annual_net_savings / installation_cost) * 100 if installation_cost > 0 else 0
    
    # Payback period in years (simplified)
    payback_years = installation_cost / annual_net_savings if annual_net_savings > 0 else 99
    
    return {
        'viable': True,
        'system_size': max_system_size,
        'annual_production': annual_production,
        'annual_savings': annual_savings,
        'installation_cost': installation_cost,
        'annual_maintenance': annual_maintenance,
        'roi_percentage': roi_percentage,
        'payback_years': payback_years,
        'expected_roi': roi_percentage
    }

def calculate_social_influence(household: Dict[str, Any], 
                             all_households: List[Dict[str, Any]], 
                             community_id: int) -> float:
    """
    Calculate the social influence factor for solar adoption.
    
    Args:
        household: Household data dictionary
        all_households: List of all household data dictionaries
        community_id: ID of the household's community
        
    Returns:
        Social influence factor (0-1)
    """
    # Get households in the same community
    community_households = [h for h in all_households 
                          if h['community_id'] == community_id and h['id'] != household['id']]
    
    if not community_households:
        return 0.5  # Neutral influence if no neighbors
    
    # Calculate adoption rate in community
    num_with_solar = sum(1 for h in community_households if h['has_solar'])
    adoption_rate = num_with_solar / len(community_households)
    
    # Calculate peer influence (0-1)
    peer_influence = min(adoption_rate * 1.5, 1.0)  # Cap at 1.0
    
    return peer_influence

def make_adoption_decision(household: Dict[str, Any],
                          adoption_metrics: Dict[str, float],
                          social_influence: float,
                          current_month: int) -> bool:
    """
    Make a decision about whether to adopt solar.
    
    Args:
        household: Household data dictionary
        adoption_metrics: Output from evaluate_solar_potential
        social_influence: Social influence factor (0-1)
        current_month: Current month (1-12)
        
    Returns:
        Boolean indicating whether to adopt solar
    """
    if household['has_solar'] or not adoption_metrics['viable']:
        return False
    
    # Base adoption probability based on ROI
    min_roi = 2.0  # Minimum ROI% to consider
    max_roi = 10.0  # ROI% at which probability is 1.0
    roi_factor = min(max((adoption_metrics['roi_percentage'] - min_roi) / (max_roi - min_roi), 0), 1)
    
    # Payback period factor (shorter is better)
    max_payback = 15.0  # Years
    payback_factor = 1.0 - min(adoption_metrics['payback_years'] / max_payback, 1.0)
    
    # Financial capacity factor
    financial_factor = household['financial_capacity']
    
    # Seasonal factor (higher in spring/summer)
    seasonal_factor = 0.5 + 0.5 * np.sin((current_month - 3) * np.pi / 6)  # Peaks in June
    
    # Calculate total adoption probability
    base_probability = 0.7 * roi_factor + 0.2 * payback_factor + 0.1 * financial_factor
    
    # Apply social influence
    social_weight = 0.3  # How much weight to give to social influence
    total_probability = base_probability * (1 - social_weight) + social_influence * social_weight
    
    # Apply seasonal variation
    total_probability = total_probability * (0.8 + 0.4 * seasonal_factor)
    
    # Make decision
    decision = np.random.random() < total_probability
    
    return decision

def update_household_adoption(household: Dict[str, Any],
                             decision: bool,
                             adoption_metrics: Dict[str, float]) -> Dict[str, Any]:
    """
    Update household state based on adoption decision.
    
    Args:
        household: Household data dictionary
        decision: Whether to adopt solar
        adoption_metrics: Output from evaluate_solar_potential
        
    Returns:
        Updated household data
    """
    if decision and not household['has_solar']:
        household['has_solar'] = True
        household['generation_capacity'] = adoption_metrics.get('system_size', 5.0)  # Default 5 kW if not specified
        household['expected_roi'] = adoption_metrics.get('roi_percentage', 5.0)
    
    return household
