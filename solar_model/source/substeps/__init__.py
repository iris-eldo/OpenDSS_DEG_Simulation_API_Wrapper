"""
Substeps package for the solar energy simulation.
Contains modules for each simulation substep.
"""

# Import all substep modules
from .solar_generation import (
    calculate_solar_generation,
    update_energy_balance,
    update_household_state
)

from .market_clearing import (
    aggregate_community_energy,
    clear_market,
    update_community_state,
    process_community
)

from .grid_interaction import (
    monitor_grid_status,
    update_grid_pricing,
    update_grid_state,
    process_grid_station
)

from .solar_adoption import (
    evaluate_solar_potential,
    calculate_social_influence,
    make_adoption_decision,
    update_household_adoption
)

from .financial_update import (
    calculate_monthly_financials,
    update_household_finances,
    update_roi_expectations
)

__all__ = [
    # Solar Generation
    'calculate_solar_generation',
    'update_energy_balance',
    'update_household_state',
    
    # Market Clearing
    'aggregate_community_energy',
    'clear_market',
    'update_community_state',
    'process_community',
    
    # Grid Interaction
    'monitor_grid_status',
    'update_grid_pricing',
    'update_grid_state',
    'process_grid_station',
    
    # Solar Adoption
    'evaluate_solar_potential',
    'calculate_social_influence',
    'make_adoption_decision',
    'update_household_adoption',
    
    # Financial Update
    'calculate_monthly_financials',
    'update_household_finances',
    'update_roi_expectations'
]
