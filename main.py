import os
import random
import shutil
import sys
from datetime import datetime
from typing import Dict, List, Union

import numpy as np
import opendssdirect as dss
import pandas as pd


# --- Utility and File Saving Functions ---

def create_output_directory(dir_name: str) -> str:
    """
    Creates a clean directory for saving results in the script's location.
    
    Args:
        dir_name (str): The name of the directory to create.
        
    Returns:
        str: The absolute path to the created directory.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    results_dir = os.path.join(script_dir, dir_name)
    if os.path.exists(results_dir):
        shutil.rmtree(results_dir)
    os.makedirs(results_dir, exist_ok=True)
    print(f"Created clean results directory at: {results_dir}")
    return results_dir


def save_to_results(content: Union[str, pd.DataFrame], directory: str, filename: str, mode: str = 'w') -> str:
    """
    Save content to a file in a specified directory with a timestamp.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    base_name, ext = os.path.splitext(filename)
    if not ext:
        ext = '.txt'

    new_filename = f"{base_name}_{timestamp}{ext}"
    filepath = os.path.join(directory, new_filename)

    try:
        with open(filepath, mode, encoding='utf-8') as f:
            if isinstance(content, pd.DataFrame):
                float_cols = content.select_dtypes(include=['float64']).columns
                content[float_cols] = content[float_cols].round(4)
                f.write(content.to_string(index=False))
            else:
                f.write(str(content))

        print(f"Results saved to: {filepath}")
        return filepath

    except Exception as e:
        print(f"Error saving results to {filepath}: {str(e)}")
        return ""


# --- OpenDSS Interaction Class ---

class OpenDSSCircuit:
    """A class to interact with an OpenDSS circuit."""

    def __init__(self, dss_file: str):
        """Initialize the OpenDSS circuit with a DSS file."""
        self.dss_file = dss_file or r"Test_Systems\IEEE 13 Bus-G\Master.DSS"
        self._initialize_dss()

    def _initialize_dss(self):
        """Initialize OpenDSS, clear previous data, and load the circuit."""
        print("Initializing OpenDSS...")
        dss.Basic.ClearAll()
        print(f"Loading circuit file: {self.dss_file}")
        try:
            dss.Text.Command(f'Compile "{self.dss_file}"')
            num_buses = dss.Circuit.NumBuses()
            if num_buses == 0:
                raise FileNotFoundError(f"No buses found. Check DSS file: {self.dss_file}")
            print(f"Successfully loaded circuit with {num_buses} buses.")
        except Exception as e:
            print(f"Error loading DSS file: {str(e)}")
            raise

    def get_buses(self) -> pd.DataFrame:
        """
        Gets all buses with detailed info from the CURRENTLY SOLVED circuit state.
        Fetches voltages in both per-unit and absolute Volts.
        """
        print("\nCollecting bus information...")
        try:
            bus_names = dss.Circuit.AllBusNames()
            if not bus_names:
                print("Warning: No buses found in the circuit!")
                return pd.DataFrame()

            buses_data = []
            for bus_name in bus_names:
                dss.Circuit.SetActiveBus(bus_name)
                num_nodes = dss.Bus.NumNodes()
                nodes = dss.Bus.Nodes()

                voltages_abs = dss.Bus.VMagAngle()
                voltages_pu = dss.Bus.puVmagAngle()

                if not voltages_abs or len(voltages_abs) < num_nodes * 2:
                    continue

                for j in range(num_nodes):
                    v_mag_abs, v_angle = voltages_abs[2 * j], voltages_abs[2 * j + 1]
                    v_mag_pu = voltages_pu[2 * j]

                    buses_data.append({
                        'Bus': bus_name,
                        'Node': nodes[j],
                        'VMag_pu': v_mag_pu,
                        'VAngle': v_angle,
                        'VMag_Volts': v_mag_abs
                    })

            df = pd.DataFrame(buses_data)
            numeric_cols = ['VMag_pu', 'VAngle', 'VMag_Volts']
            for col in numeric_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            return df
        except Exception as e:
            print(f"\nError in get_buses(): {str(e)}")
            return pd.DataFrame()

    def modify_source_voltage(self, pu_voltage: float):
        """
        Modifies the main Vsource element's per-unit voltage.
        """
        try:
            dss.Text.Command(f"Vsource.source.pu={pu_voltage}")
            print(f"\nModifying main source voltage to {pu_voltage:.4f} p.u.")
        except Exception as e:
            print(f"Error modifying source voltage: {str(e)}")

    def add_load(self, bus_name: str, kw: float, kvar: float, phases: int = 3, kv: float = 4.16):
        """Adds a load to a specific bus."""
        load_name = f"Load_{bus_name}_{kw}kW"
        command = (
            f'New Load.{load_name} '
            f'bus1={bus_name}.1.2.3 phases={phases} conn=wye model=1 '
            f'kv={kv} kw={kw} kvar={kvar} status=variable'
        )
        dss.Text.Command(command)
        print(f"Adding new load '{load_name}' to bus {bus_name}.")

    def node_disconnect(self, exclude_buses: List[str]) -> str:
        """
        Randomly disconnects a Line element from the circuit.
        """
        all_lines = dss.Lines.AllNames()
        
        candidate_lines = []
        for line in all_lines:
            dss.Circuit.SetActiveElement(f"Line.{line}")
            bus_names = [b.split('.')[0] for b in dss.CktElement.BusNames()]
            if not any(bus in exclude_buses for bus in bus_names):
                candidate_lines.append(line)

        if not candidate_lines:
            return "No candidate lines found to disconnect."

        line_to_disconnect = random.choice(candidate_lines)
        dss.Circuit.SetActiveElement(f"Line.{line_to_disconnect}")
        dss.CktElement.Enabled(False)
        
        return f"Disconnected Line.{line_to_disconnect} from the circuit."

    def solve_power_flow(self, max_iterations: int = 100) -> bool:
        """Solves the power flow and returns the convergence status."""
        print("\nSolving power flow...")
        dss.Text.Command(f'set maxiter={max_iterations}')
        dss.Solution.Solve()
        converged = dss.Solution.Converged()
        if converged:
            print("Power flow converged successfully.")
        else:
            print("WARNING: Power flow did not converge.")
        return converged

    def get_power_flow_results(self) -> Dict:
        """Gets comprehensive power flow results."""
        total_p, total_q = dss.Circuit.TotalPower()
        return {
            'converged': dss.Solution.Converged(),
            'iterations': dss.Solution.Iterations(),
            'total_circuit_power_kW': total_p,
            'total_circuit_power_kVAR': total_q,
            'total_power_losses_kW': dss.Circuit.Losses()[0] / 1000,
            'total_reactive_losses_kVAR': dss.Circuit.Losses()[1] / 1000,
        }


# --- Reporting Functions ---

def print_bus_table(buses_df: pd.DataFrame, title: str = "Bus Information"):
    """Prints bus information in a formatted table to the console."""
    if buses_df.empty:
        print("No bus data available to print.")
        return
    print(f"\n{'='*80}\n{title:^80}\n{'='*80}")
    display_cols = ['Bus', 'Node', 'VMag_pu', 'VAngle']
    formatted_df = buses_df[display_cols].copy()
    formatted_df['VMag_pu'] = formatted_df['VMag_pu'].apply(lambda x: f"{x:.4f} pu")
    formatted_df['VAngle'] = formatted_df['VAngle'].apply(lambda x: f"{x:.2f}°")
    print(formatted_df.to_string(index=False))
    print(f"{'='*80}")


def save_bus_details(buses_df: pd.DataFrame, directory: str, filename: str):
    """Saves detailed bus information to a text file."""
    if buses_df.empty:
        return

    output = [f"{'='*80}", f"BUS DETAILS - {pd.Timestamp.now()}", f"{'='*80}\n"]
    output.append(f"Total bus-node pairs: {len(buses_df)}")
    output.append(f"Total unique buses: {buses_df['Bus'].nunique()}\n")
    output.append("DETAILED BUS INFORMATION\n" + "-" * 80)

    display_cols = ['Bus', 'Node', 'VMag_pu', 'VAngle', 'VMag_Volts']
    formatted_df = buses_df[display_cols].copy()
    formatted_df['VMag_pu'] = formatted_df['VMag_pu'].map('{:.6f}'.format)
    formatted_df['VAngle'] = formatted_df['VAngle'].map('{:.4f}°'.format)
    formatted_df['VMag_Volts'] = formatted_df['VMag_Volts'].map('{:,.2f}'.format)
    output.append(formatted_df.to_string(index=False))

    save_to_results("\n".join(output), directory, filename)


def save_power_flow_results(results: dict, buses_df: pd.DataFrame, directory: str):
    """Saves comprehensive, formatted power flow results to a file."""
    p = results['total_circuit_power_kW']
    q = results['total_circuit_power_kVAR']
    s = np.sqrt(p ** 2 + q ** 2)
    power_factor = abs(p / s if s > 0 else 0)
    pf_type = "Lagging" if q > 0 else "Leading"

    min_v = buses_df['VMag_pu'].min()
    max_v = buses_df['VMag_pu'].max()
    avg_v = buses_df['VMag_pu'].mean()
    min_bus_info = buses_df.loc[buses_df['VMag_pu'].idxmin()]
    max_bus_info = buses_df.loc[buses_df['VMag_pu'].idxmax()]

    output = [
        f"{'=' * 80}", f"{'COMPREHENSIVE POWER FLOW RESULTS':^80}", f"{'=' * 80}",
        "\n--- SOLUTION ---",
        f"Converged: {'Yes' if results['converged'] else 'No'}",
        f"Iterations: {results['iterations']}",

        "\n--- POWER SUMMARY ---",
        f"Total Circuit Power: {p:.2f} kW, {q:.2f} kVAR",
        f"Overall Power Factor: {power_factor:.4f} {pf_type}",
        f"Total Power Losses:  {results['total_power_losses_kW']:.2f} kW",
        f"Total Reactive Losses: {results['total_reactive_losses_kVAR']:.2f} kVAR",

        "\n--- VOLTAGE PROFILE (p.u.) ---",
        f"Minimum Voltage: {min_v:.4f} pu at Bus '{min_bus_info['Bus']}' (Node {min_bus_info['Node']})",
        f"Maximum Voltage: {max_v:.4f} pu at Bus '{max_bus_info['Bus']}' (Node {max_bus_info['Node']})",
        f"Average Voltage: {avg_v:.4f} pu",
        f"{'=' * 80}"
    ]
    save_to_results("\n".join(output), directory, "power_flow_results.txt")


def save_voltage_comparison(df_before: pd.DataFrame, df_after: pd.DataFrame, directory: str):
    """Compares two bus dataframes and saves a detailed report."""
    if df_before.empty or df_after.empty:
        return
        
    # Use the per-unit voltage for a standardized comparison
    comparison = pd.merge(
        df_before[['Bus', 'Node', 'VMag_pu', 'VAngle']],
        df_after[['Bus', 'Node', 'VMag_pu', 'VAngle']],
        on=['Bus', 'Node'], suffixes=('_initial', '_modified')
    )
    comparison['Vdiff_pu'] = comparison['VMag_pu_modified'] - comparison['VMag_pu_initial']
    comparison['Angle_diff_deg'] = comparison['VAngle_modified'] - comparison['VAngle_initial']

    output = [f"{'=' * 80}", f"{'VOLTAGE COMPARISON (INITIAL VS MODIFIED)':^80}", f"{'=' * 80}\n"]
    output.append(comparison.round(4).to_string(index=False))
    save_to_results("\n".join(output), directory, "voltage_comparison.txt")


# --- Simulation Logic ---

def run_initial_simulation(circuit: OpenDSSCircuit, results_dir: str) -> pd.DataFrame:
    """Runs a basic simulation and saves all results."""
    print("\n" + "=" * 50)
    print("--- 1. Starting Initial Simulation ---")
    print("=" * 50)

    circuit.solve_power_flow()
    pf_results = circuit.get_power_flow_results()
    initial_buses_df = circuit.get_buses()

    print_bus_table(initial_buses_df, "Initial Bus Voltages")
    save_bus_details(initial_buses_df, results_dir, "initial_bus_details.txt")
    save_power_flow_results(pf_results, initial_buses_df, results_dir)

    print("\n--- Initial Simulation Complete ---")
    return initial_buses_df


def run_modified_simulation(circuit: OpenDSSCircuit, initial_buses_df: pd.DataFrame, results_dir: str):
    """Modifies the circuit, runs a new simulation, and saves all results."""
    print("\n" + "=" * 50)
    print("--- 2. Starting Modified Simulation ---")
    print("=" * 50)

    # Modify the main source voltage
    circuit.modify_source_voltage(pu_voltage=1.05)

    # Add a new load
    circuit.add_load(bus_name='671', kw=500, kvar=200)

    # Disconnect a random node (by disabling a line)
    print("\nPerforming random node disconnection...")
    disconnection_message = circuit.node_disconnect(exclude_buses=['sourcebus'])
    print(disconnection_message)

    # Solve the modified circuit
    circuit.solve_power_flow()
    
    # Get and save all results for the modified circuit
    pf_results_mod = circuit.get_power_flow_results()
    modified_buses_df = circuit.get_buses()

    print_bus_table(modified_buses_df, "Modified Bus Voltages (After All Changes)")
    save_bus_details(modified_buses_df, results_dir, "modified_bus_details.txt")
    save_power_flow_results(pf_results_mod, modified_buses_df, results_dir)
    save_voltage_comparison(initial_buses_df, modified_buses_df, results_dir)

    print("\n--- Modified Simulation Complete ---")


# --- Main Execution ---

def main():
    """Main function to orchestrate the OpenDSS simulations."""
    try:
        # Setup clean output directories
        initial_results_dir = create_output_directory("results")
        modified_results_dir = create_output_directory("results_modified")

        # Initialize the circuit once
        circuit = OpenDSSCircuit("")

        # Run the initial simulation to get a baseline
        initial_buses_df = run_initial_simulation(circuit, initial_results_dir)

        # Run the second simulation with modifications
        run_modified_simulation(circuit, initial_buses_df, modified_results_dir)

        print("\nAll simulations finished successfully.")

    except Exception as e:
        print(f"\nAn unexpected error occurred in main: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Ensure __file__ is defined for pathing
    if '__file__' not in locals():
        __file__ = os.path.abspath('__main__')
    main()