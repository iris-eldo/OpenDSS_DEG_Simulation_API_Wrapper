"""
Metrics and results calculation for the solar energy simulation.
Handles calculation of various performance metrics and saving results.
"""
import os
import numpy as np
import pandas as pd
from typing import Dict, Any, List

def calculate_metrics(state: Dict[str, Any], step: int) -> Dict[str, float]:
    """
    Calculate metrics for the current simulation state.
    
    Args:
        state: Current simulation state
        step: Current simulation step
        
    Returns:
        Dictionary of calculated metrics
    """
    household = state['household']
    community = state['community']
    grid = state['grid_station']
    
    # Calculate adoption metrics
    num_households = len(household['has_solar'])
    num_with_solar = np.sum(household['has_solar'])
    solar_adoption_rate = num_with_solar / num_households if num_households > 0 else 0
    
    # Energy metrics
    total_generation = np.sum(household['generation_capacity'][household['has_solar']]) * 30 * 24  # Approximate monthly
    energy_sold = np.sum(household['excess_energy'])
    energy_consumed = np.sum(household['grid_consumption'])
    
    # Financial metrics
    total_savings = np.sum(household['cumulative_savings'])
    avg_roi = np.mean(household['expected_roi'][household['has_solar']]) if num_with_solar > 0 else 0
    
    # Grid metrics
    grid_load = np.sum(grid['current_load'])
    grid_revenue = np.sum(grid['revenue'])
    
    return {
        'step': step,
        'solar_adoption_rate': float(solar_adoption_rate),
        'num_households_with_solar': int(num_with_solar),
        'total_generation': float(total_generation),
        'energy_sold': float(energy_sold),
        'energy_consumed': float(energy_consumed),
        'total_savings': float(total_savings),
        'avg_roi': float(avg_roi),
        'grid_load': float(grid_load),
        'grid_revenue': float(grid_revenue),
        'avg_market_price': float(np.mean(community['market_price']))
    }

def save_results(results: List[Dict[str, float]], output_file: str = 'results.csv') -> None:
    """
    Save simulation results to a CSV file.
    
    Args:
        results: List of metric dictionaries
        output_file: Path to the output CSV file
    """
    if not results:
        print("No results to save.")
        return
    
    # Convert to DataFrame and save
    df = pd.DataFrame(results)
    df.to_csv(output_file, index=False)
    print(f"Results saved to {os.path.abspath(output_file)}")

def calculate_financial_metrics(household_data: Dict[str, Any], 
                              community_data: Dict[str, Any],
                              config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate financial metrics for households.
    
    Args:
        household_data: Household data dictionary
        community_data: Community data dictionary
        config: Simulation configuration
        
    Returns:
        Updated household data with financial metrics
    """
    # Calculate monthly costs and savings
    grid_price = config['environment']['grid_buy_price']
    sell_ratio = config['environment']['grid_sell_ratio']
    
    # Calculate monthly costs without solar
    monthly_costs_no_solar = household_data['demand_profile'][:, 0] * grid_price  # Using first month as example
    
    # Calculate actual monthly costs with solar
    monthly_costs = (
        household_data['grid_consumption'] * grid_price -
        household_data['excess_energy'] * grid_price * sell_ratio
    )
    
    # Calculate monthly savings
    monthly_savings = monthly_costs_no_solar - monthly_costs
    
    # Update household data
    household_data['monthly_savings'] = monthly_savings
    household_data['cumulative_savings'] += monthly_savings
    
    # Update ROI for households with solar
    solar_mask = household_data['has_solar']
    if np.any(solar_mask):
        # Simple ROI calculation: (savings - cost) / cost * 100
        installation_cost = (
            household_data['generation_capacity'][solar_mask] * 1000 *  # kW to W
            config['environment']['solar_installation_cost']
        )
        
        # Annual savings (assuming savings are representative of monthly average)
        annual_savings = monthly_savings[solar_mask] * 12
        
        # ROI in percentage (annual savings / cost * 100)
        household_data['expected_roi'][solar_mask] = (
            (annual_savings / installation_cost) * 100
        )
    
    return household_data
