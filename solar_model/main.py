"""
Main module for the solar energy adoption simulation using AgentTorch.
"""
import os
import sys
import yaml
import numpy as np
import pandas as pd
import torch
from typing import Dict, Any, List, Tuple

# Add source directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import AgentTorch components
from agent_torch.core import Registry, Runner
from agent_torch.core.helpers import read_from_file

# Import utilities
from source.utilities import load_config, validate_config, calculate_metrics, save_results

# Import format utilities if available, otherwise define placeholders
try:
    from source.utilities.format import display_metrics, inspect_tensor
except ImportError:
    # Define simple placeholders if format module is not available
    def display_metrics(metrics):
        print("Metrics:", metrics)
    
    def inspect_tensor(name, tensor):
        print(f"{name}:", type(tensor))
        if hasattr(tensor, 'shape'):
            print(f"  Shape: {tensor.shape}")
        if hasattr(tensor, 'dtype'):
            print(f"  Dtype: {tensor.dtype}")

# Import substeps
from source.substeps import (
    calculate_solar_generation as original_calculate_solar_generation,
    update_energy_balance, update_household_state,
    aggregate_community_energy, clear_market, update_community_state,
    process_community, process_grid_station, evaluate_solar_potential,
    calculate_social_influence, make_adoption_decision, update_household_adoption,
    calculate_monthly_financials, update_household_finances, update_roi_expectations
)
from typing import Dict, Any, Tuple

def calculate_solar_generation(config: Dict[str, Any], input_vars: Dict[str, Any], 
                             output_vars: Dict[str, Any], args: Dict[str, Any]) -> Tuple[float, float]:
    """Wrapper function for calculate_solar_generation that matches AgentTorch's expected signature."""
    # Extract household and current_month from input_vars
    household = input_vars['household']
    current_month = input_vars['current_month']
    
    # Call the original function
    return original_calculate_solar_generation(household, current_month)

# Configuration
CONFIG_FILE = os.path.join(os.path.dirname(__file__), 'config', 'solar.yaml')

def main():
    """Main entry point for the simulation."""
    # Set random seeds for reproducibility
    torch.manual_seed(42)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(42)
    np.random.seed(42)
    
    try:
        # Load and validate configuration
        config = load_config(CONFIG_FILE)
        validate_config(config)
        
        # Initialize registry
        registry = Registry()
        
        # Register initialization function
        registry.register(read_from_file, 'read_from_file', 'initialization')
        
        # Register observation helpers
        registry.register(calculate_solar_generation, 'calculate_solar_generation', 'observation')
        registry.register(aggregate_community_energy, 'aggregate_community_energy', 'observation')
        registry.register(update_energy_balance, 'update_energy_balance', 'observation')
        
        # Register policy helpers
        registry.register(clear_market, 'clear_market', 'policy')
        registry.register(evaluate_solar_potential, 'evaluate_solar_potential', 'policy')
        registry.register(calculate_social_influence, 'calculate_social_influence', 'policy')
        registry.register(make_adoption_decision, 'make_adoption_decision', 'policy')
        
        # Register transition helpers
        registry.register(update_household_state, 'update_household_state', 'transition')
        registry.register(update_community_state, 'update_community_state', 'transition')
        registry.register(process_community, 'process_community', 'transition')
        registry.register(process_grid_station, 'process_grid_station', 'transition')
        registry.register(update_household_adoption, 'update_household_adoption', 'transition')
        registry.register(calculate_monthly_financials, 'calculate_monthly_financials', 'transition')
        registry.register(update_household_finances, 'update_household_finances', 'transition')
        registry.register(update_roi_expectations, 'update_roi_expectations', 'transition')
        
        # Prepare configuration for AgentTorch
        parsed = {
            'simulation_metadata': {
                'num_substeps_per_step': len(config.get('substeps', [])),
                'current_step': 0,
                'current_substep': 0,
                'device': 'cuda' if torch.cuda.is_available() else 'cpu',
                'dtype': 'float32',
                'seed': 42
            },
            'simulation': {
                'steps': config['simulation']['steps'],
                'substeps': [step.get('name') for step in config.get('substeps', []) if 'name' in step]
            },
            'state': {
                'environment': {},
                'agents': {},
                'objects': {},
                'network': {}
            },
            'substeps': {
                step['name']: {
                    'name': step['name'],
                    'active_agents': [step['agent']],
                    'observation': {
                        step['agent']: {
                            step['observation']['func']: {
                                'generator': step['observation']['func'],
                                'arguments': None,
                                'input_variables': {
                                    var.split('/')[-1]: var 
                                    for var in step['observation'].get('observes', [])},
                                'output_variables': step['observation'].get('produces', [])
                            }
                        } if 'observation' in step and 'func' in step['observation'] else None
                    },
                    'policy': {
                        step['agent']: {
                            step['action']['func']: {
                                'generator': step['action']['func'],
                                'arguments': None,
                                'input_variables': {
                                    var.split('/')[-1]: var 
                                    for var in step['action'].get('requires', [])},
                                'output_variables': step['action'].get('decides', [])
                            }
                        } if 'action' in step and 'func' in step['action'] else None
                    },
                    'transition': {
                        step['transition']['func']: {
                            'generator': step['transition']['func'],
                            'arguments': None,
                            'input_variables': {
                                var.split('/')[-1]: var 
                                for var in step['transition'].get('updates', [])},
                            'output_variables': [var.split('/')[-1] for var in step['transition'].get('updates', [])]
                        }
                    } if 'transition' in step and 'func' in step['transition'] else {}
                }
                for step in config.get('substeps', []) if 'name' in step and 'agent' in step
            }
        }
        
        # Initialize and run the simulation
        print("Starting solar energy adoption simulation...")
        print(f"Simulation steps: {config['simulation']['steps']}")
        
        runner = Runner(parsed, registry)
        runner.init()
        
        # Run simulation steps
        steps = config['simulation']['steps']
        for step in range(steps):
            runner.step(1)
            
            # Get current state and calculate metrics
            current_state = runner.state_trajectory[-1][-1] if runner.state_trajectory else {}
            
            # Print progress
            if (step + 1) % 10 == 0 or step == 0 or step == steps - 1:
                print(f"\n--- Step {step + 1}/{steps} ---")
                if current_state:
                    inspect_tensor(f'State at step {step}', current_state)
                    try:
                        metrics = calculate_metrics(current_state)
                        display_metrics(metrics)
                    except Exception as e:
                        print(f"Error calculating metrics: {e}")
        
        # Save results if we have state trajectory
        if hasattr(runner, 'state_trajectory') and runner.state_trajectory:
            save_results(runner.state_trajectory, 'results.csv')
            print("\nSimulation completed. Results saved to 'results.csv'")
        else:
            print("\nSimulation completed. No state trajectory to save.")
        
    except Exception as e:
        print(f"Error running simulation: {str(e)}", file=sys.stderr)
        if torch.cuda.is_available():
            print(f"GPU Memory Usage: \n{torch.cuda.memory_summary()}")
        raise

if __name__ == "__main__":
    main()
