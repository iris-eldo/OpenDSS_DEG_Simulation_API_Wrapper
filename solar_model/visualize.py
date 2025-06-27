"""
Visualization script for the solar energy simulation results.
Generates plots and charts to analyze the simulation output.
"""
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Optional

def load_results(filepath: str = 'results.csv') -> pd.DataFrame:
    """Load simulation results from a CSV file.
    
    Args:
        filepath: Path to the results CSV file
        
    Returns:
        DataFrame containing the simulation results
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Results file not found: {filepath}")
    return pd.read_csv(filepath)

def plot_solar_adoption(results: pd.DataFrame, output_file: Optional[str] = None) -> None:
    """Plot the solar adoption rate over time.
    
    Args:
        results: DataFrame containing simulation results
        output_file: Optional path to save the plot
    """
    plt.figure(figsize=(10, 6))
    
    # Plot solar adoption rate
    plt.plot(results['step'], results['solar_adoption_rate'] * 100, 
             marker='o', label='Solar Adoption Rate')
    
    plt.title('Solar Panel Adoption Over Time')
    plt.xlabel('Simulation Step (Month)')
    plt.ylabel('Adoption Rate (%)')
    plt.grid(True)
    plt.legend()
    
    if output_file:
        plt.savefig(output_file, bbox_inches='tight')
        print(f"Plot saved to {output_file}")
    else:
        plt.show()

def plot_energy_metrics(results: pd.DataFrame, output_file: Optional[str] = None) -> None:
    """Plot energy generation and consumption metrics.
    
    Args:
        results: DataFrame containing simulation results
        output_file: Optional path to save the plot
    """
    plt.figure(figsize=(12, 8))
    
    # Create subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot generation and consumption
    ax1.plot(results['step'], results['total_generation'], 'g-', label='Total Generation')
    ax1.plot(results['step'], results['energy_consumed'], 'b-', label='Energy Consumed')
    ax1.set_title('Energy Generation and Consumption')
    ax1.set_xlabel('Simulation Step (Month)')
    ax1.set_ylabel('Energy (kWh)')
    ax1.legend()
    ax1.grid(True)
    
    # Plot energy sold
    ax2.plot(results['step'], results['energy_sold'], 'r-', label='Energy Sold to Grid')
    ax2.set_title('Energy Sold to Grid')
    ax2.set_xlabel('Simulation Step (Month)')
    ax2.set_ylabel('Energy (kWh)')
    ax2.legend()
    ax2.grid(True)
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, bbox_inches='tight')
        print(f"Plot saved to {output_file}")
    else:
        plt.show()

def plot_financial_metrics(results: pd.DataFrame, output_file: Optional[str] = None) -> None:
    """Plot financial metrics over time.
    
    Args:
        results: DataFrame containing simulation results
        output_file: Optional path to save the plot
    """
    plt.figure(figsize=(12, 8))
    
    # Create subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot total savings
    ax1.plot(results['step'], results['total_savings'], 'g-', label='Total Savings ($)')
    ax1.set_title('Total Savings Over Time')
    ax1.set_xlabel('Simulation Step (Month)')
    ax1.set_ylabel('Savings ($)')
    ax1.legend()
    ax1.grid(True)
    
    # Plot ROI
    ax2.plot(results['step'], results['avg_roi'], 'b-', label='Average ROI (%)')
    ax2.set_title('Average Return on Investment (ROI)')
    ax2.set_xlabel('Simulation Step (Month)')
    ax2.set_ylabel('ROI (%)')
    ax2.legend()
    ax2.grid(True)
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, bbox_inches='tight')
        print(f"Plot saved to {output_file}")
    else:
        plt.show()

def plot_grid_metrics(results: pd.DataFrame, output_file: Optional[str] = None) -> None:
    """Plot grid-related metrics.
    
    Args:
        results: DataFrame containing simulation results
        output_file: Optional path to save the plot
    """
    plt.figure(figsize=(12, 8))
    
    # Create subplots
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot grid load
    ax1.plot(results['step'], results['grid_load'], 'r-', label='Grid Load (kW)')
    ax1.set_title('Grid Load Over Time')
    ax1.set_xlabel('Simulation Step (Month)')
    ax1.set_ylabel('Load (kW)')
    ax1.legend()
    ax1.grid(True)
    
    # Plot market price
    ax2.plot(results['step'], results['avg_market_price'] * 100, 'm-', 
             label='Average Market Price (¢/kWh)')
    ax2.set_title('Average Market Price')
    ax2.set_xlabel('Simulation Step (Month)')
    ax2.set_ylabel('Price (¢/kWh)')
    ax2.legend()
    ax2.grid(True)
    
    plt.tight_layout()
    
    if output_file:
        plt.savefig(output_file, bbox_inches='tight')
        print(f"Plot saved to {output_file}")
    else:
        plt.show()

def generate_all_plots(results_file: str = 'results.csv', 
                      output_dir: str = 'plots') -> None:
    """Generate all plots and save them to the output directory.
    
    Args:
        results_file: Path to the results CSV file
        output_dir: Directory to save the output plots
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Load results
    results = load_results(results_file)
    
    # Generate and save plots
    plot_solar_adoption(results, os.path.join(output_dir, 'solar_adoption.png'))
    plot_energy_metrics(results, os.path.join(output_dir, 'energy_metrics.png'))
    plot_financial_metrics(results, os.path.join(output_dir, 'financial_metrics.png'))
    plot_grid_metrics(results, os.path.join(output_dir, 'grid_metrics.png'))
    
    print(f"All plots saved to {os.path.abspath(output_dir)}/")

if __name__ == "__main__":
    # Example usage
    try:
        # Generate all plots and save to 'plots' directory
        generate_all_plots()
        
        # Or load results and display a specific plot
        # results = load_results()
        # plot_solar_adoption(results)
        # plot_energy_metrics(results)
        # plot_financial_metrics(results)
        # plot_grid_metrics(results)
        
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Please run the simulation first to generate results.csv")
