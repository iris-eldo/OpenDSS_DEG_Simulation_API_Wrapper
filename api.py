import os
import pandas as pd
from flask import Flask, request, jsonify
from simulation_core import OpenDSSCircuit

# --- Global Application Setup ---
app = Flask(__name__)

# Create a dedicated directory for API results
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results_api')
os.makedirs(RESULTS_DIR, exist_ok=True)

print("--- Initializing Global OpenDSS Circuit (Do Not Use in Production) ---")
circuit = OpenDSSCircuit("")
circuit.solve_power_flow()
print("--- Initial Baseline Simulation Complete. API is Ready. ---")


def get_current_state_details(circuit_object: OpenDSSCircuit) -> dict:
    """Helper function to gather results from the current circuit state."""
    pf_results = circuit_object.get_power_flow_results()
    buses_df = circuit_object.get_buses_with_loads()

    power_summary = {
        "converged": pf_results['converged'],
        "total_circuit_power_kW": round(pf_results['total_power_kW'], 2),
        "total_losses_kW": round(pf_results['total_losses_kW'], 4),
        "total_load_kW": round(buses_df['Load_kW'].sum(), 2),
    }
    voltage_profile = {
        "min_voltage_pu": round(buses_df['VMag_pu'].min(), 4),
        "max_voltage_pu": round(buses_df['VMag_pu'].max(), 4),
        "avg_voltage_pu": round(buses_df['VMag_pu'].mean(), 4),
    }
    bus_details = buses_df.round(4).to_dict(orient='records')

    return {
        "power_summary": power_summary,
        "voltage_profile": voltage_profile,
        "bus_details": bus_details
    }

def save_state_to_file(state_details: dict, filename: str):
    """Formats and saves the current state to a single, overwritable text file."""
    filepath = os.path.join(RESULTS_DIR, filename)
    summary = state_details['power_summary']
    voltage = state_details['voltage_profile']
    bus_df = pd.DataFrame(state_details['bus_details'])

    output = [
        f"{'='*110}",
        f"SIMULATION STATE REPORT",
        f"{'='*110}\n",
        "--- POWER SUMMARY ---",
        f"Converged: {summary.get('converged')}",
        f"Total Circuit Power: {summary.get('total_circuit_power_kW'):.2f} kW",
        f"Total Load: {summary.get('total_load_kW'):.2f} kW",
        f"Total Losses: {summary.get('total_losses_kW'):.2f} kW\n",
        "--- VOLTAGE PROFILE ---",
        f"Min/Avg/Max Voltage (p.u.): {voltage.get('min_voltage_pu'):.4f} / {voltage.get('avg_voltage_pu'):.4f} / {voltage.get('max_voltage_pu'):.4f}\n",
        "--- DETAILED BUS DATA ---",
        bus_df.to_string(index=False)
    ]

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("\n".join(output))
    print(f"Results updated in file: {filepath}")


# --- API Endpoints ---

@app.route('/modify_load_neighbourhood', methods=['POST'])
def modify_load_endpoint():
    data = request.get_json()
    try:
        neighbourhood = int(data['neighbourhood'])
        factor = float(data['factor'])
    except (TypeError, KeyError, ValueError):
        return jsonify({"status": "error", "message": "Invalid payload. Expects 'neighbourhood' (int) and 'factor' (float)."}), 400

    print(f"\n--- API CALL: /modify_load_neighbourhood (Neighborhood: {neighbourhood}, Factor: {factor}) ---")
    circuit.modify_loads_in_neighborhood(neighbourhood, factor)
    circuit.solve_power_flow()
    current_details = get_current_state_details(circuit)
    save_state_to_file(current_details, "latest_api_results.txt") # ADDED: Save results to file
    
    return jsonify({"status": "success", "results": current_details}), 200


@app.route('/add_generator', methods=['POST'])
def add_generator_endpoint():
    data = request.get_json()
    try:
        bus_name = str(data['bus_name'])
        phases = int(data['phases'])
        kw = float(data['kw'])
    except (TypeError, KeyError, ValueError):
        return jsonify({"status": "error", "message": "Invalid payload. Expects 'bus_name', 'phases', and 'kw'."}), 400

    print(f"\n--- API CALL: /add_generator (Bus: {bus_name}, Phases: {phases}, kW: {kw}) ---")
    circuit.add_generation_to_bus(bus_name, kw, phases)
    circuit.solve_power_flow()
    current_details = get_current_state_details(circuit)
    save_state_to_file(current_details, "latest_api_results.txt") # ADDED: Save results to file

    return jsonify({"status": "success", "results": current_details}), 200
'''
@app.route('/reset_simulation', methods=['POST'])
def reset_simulation_endpoint():
    global circuit
    
    print("\n--- API CALL: /reset_simulation ---")
    circuit = OpenDSSCircuit("")
    circuit.solve_power_flow()
    current_details = get_current_state_details(circuit)
    save_state_to_file(current_details, "latest_api_results.txt") # ADDED: Save results to file
    
    return jsonify({"status": "success", "message": "Circuit has been reset to its initial state.", "results": current_details})
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)