import os
import pandas as pd
from flask import Flask, request, jsonify
from main import OpenDSSCircuit

# --- Global Application Setup ---
app = Flask(__name__)
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results_api')
os.makedirs(RESULTS_DIR, exist_ok=True)

print("--- Initializing Global OpenDSS Circuit ---")
# The circuit object now manages an internal list of devices
circuit = OpenDSSCircuit("")
circuit.solve_power_flow() 
print("--- Initial Baseline Simulation Complete. API is Ready. ---")


def get_current_state_details(circuit_object: OpenDSSCircuit) -> dict:
    """Helper function to gather results from the current circuit state."""
    pf_results = circuit_object.get_power_flow_results()
    buses_df = circuit_object.get_buses_with_loads()
    
    total_load_kw = buses_df['Load_kW'].sum()
    
    power_summary = {
        "converged": pf_results['converged'],
        "total_circuit_power_kW": round(pf_results['total_power_kW'], 2),
        "total_losses_kW": round(pf_results['total_losses_kW'], 4),
        "total_load_kW": round(total_load_kw, 2),
    }
    voltage_profile = {
        "min_voltage_pu": round(buses_df['VMag_pu'].min(), 4),
        "max_voltage_pu": round(buses_df['VMag_pu'].max(), 4),
        "avg_voltage_pu": round(buses_df['VMag_pu'].mean(), 4),
    }
    
    # Sort buses for consistent output before converting to dictionary
    buses_df['Bus_numeric'] = pd.to_numeric(buses_df['Bus'].str.extract(r'(\d+)')[0], errors='coerce')
    buses_df = buses_df.sort_values(by=['Bus_numeric', 'Node']).drop(columns=['Bus_numeric'])
    bus_details = buses_df.round(4).to_dict(orient='records')

    return {
        "power_summary": power_summary,
        "voltage_profile": voltage_profile,
        "bus_details": bus_details
    }

def save_state_to_file(state_details: dict, filename: str):
    """Formats and saves the current state to a single, overwritable text file."""
    filepath = os.path.join(RESULTS_DIR, filename)
    summary, voltage, bus_list = state_details['power_summary'], state_details['voltage_profile'], state_details['bus_details']
    output = [f"{'='*120}\nSIMULATION STATE REPORT\n{'='*120}\n", "--- POWER SUMMARY ---", f"Converged: {summary.get('converged')}", f"Total Circuit Power: {summary.get('total_circuit_power_kW'):.2f} kW", f"Total Load: {summary.get('total_load_kW'):.2f} kW", f"Total Losses: {summary.get('total_losses_kW'):.2f} kW\n", "--- VOLTAGE PROFILE ---", f"Min/Avg/Max Voltage (p.u.): {voltage.get('min_voltage_pu'):.4f} / {voltage.get('avg_voltage_pu'):.4f} / {voltage.get('max_voltage_pu'):.4f}\n", "--- DETAILED BUS & NODE DATA ---"]
    header = f"{'Bus':<10}{'Node':<5}{'VMag (pu)':<15}{'VAngle (deg)':<15}{'Load (kW)':<15}{'Gen (kW)':<15}"
    output.append(header); output.append("-" * len(header))
    for bus_info in bus_list:
        output.append(f"{bus_info.get('Bus', ''):<10}{bus_info.get('Node', ''):<5}{bus_info.get('VMag_pu', 0):<15.4f}{bus_info.get('VAngle', 0):<15.2f}{bus_info.get('Load_kW', 0):<15.2f}{bus_info.get('Gen_kW', 0):<15.2f}")
        # Display devices associated with the bus
        if bus_info.get('Devices'):
            # This check prevents printing the device list for each node of the same bus
            if bus_info.get('Node') == 1 or bus_info.get('Node') == '1':
                for device in bus_info['Devices']:
                    output.append(f"  -> {'Device: ' + device.get('device_name', ''):<20} {'':<15}{'':<15} {device.get('kw', 0):<15.2f}")
    with open(filepath, 'w', encoding='utf-8') as f: f.write("\n".join(output))
    print(f"Results updated in file: {filepath}")

# --- API Endpoints ---

@app.route('/modify_load_neighbourhood', methods=['POST'])
def modify_load_endpoint():
    data = request.get_json()
    try:
        neighbourhood, factor = int(data['neighbourhood']), float(data['factor'])
    except (TypeError, KeyError, ValueError):
        return jsonify({"status": "error", "message": "Invalid payload."}), 400
    circuit.modify_loads_in_neighborhood(neighbourhood, factor)
    circuit.solve_power_flow()
    current_details = get_current_state_details(circuit)
    save_state_to_file(current_details, "latest_api_results.txt")
    return jsonify({"status": "success", "results": current_details}), 200

@app.route('/add_generator', methods=['POST'])
def add_generator_endpoint():
    data = request.get_json()
    try:
        bus_name, phases, kw = str(data['bus_name']), int(data['phases']), float(data['kw'])
    except (TypeError, KeyError, ValueError):
        return jsonify({"status": "error", "message": "Invalid payload."}), 400
    circuit.add_generation_to_bus(bus_name, kw, phases)
    circuit.solve_power_flow()
    current_details = get_current_state_details(circuit)
    save_state_to_file(current_details, "latest_api_results.txt")
    return jsonify({"status": "success", "results": current_details}), 200

@app.route('/add_device', methods=['POST'])
def add_device_endpoint():
    data = request.get_json()
    try:
        bus_name, device_name, phases, kw = str(data['bus_name']), str(data['device_name']), int(data['phases']), float(data['kw'])
    except (TypeError, KeyError, ValueError):
        return jsonify({"status": "error", "message": "Invalid payload."}), 400
    circuit.add_device_to_bus(bus_name, device_name, kw, phases)
    circuit.solve_power_flow()
    current_details = get_current_state_details(circuit)
    save_state_to_file(current_details, "latest_api_results.txt")
    return jsonify({"status": "success", "results": current_details}), 200

# --- NEW ENDPOINT ---
@app.route('/disconnect_device', methods=['POST'])
def disconnect_device_endpoint():
    """
    API endpoint to disconnect a device from a bus.
    Expects JSON payload: {"bus_name": "...", "device_name": "..."}
    """
    data = request.get_json()
    try:
        bus_name = str(data['bus_name'])
        device_name = str(data['device_name'])
    except (TypeError, KeyError, ValueError):
        return jsonify({"status": "error", "message": "Invalid payload. 'bus_name' and 'device_name' are required."}), 400

    # Call the new method in the simulation core
    was_disconnected = circuit.disconnect_device_from_bus(bus_name, device_name)

    if not was_disconnected:
        return jsonify({"status": "not_found", "message": f"Device '{device_name}' not found on bus '{bus_name}'."}), 404

    # Re-run power flow and get the updated state
    circuit.solve_power_flow()
    current_details = get_current_state_details(circuit)
    save_state_to_file(current_details, "latest_api_results.txt")

    return jsonify({
        "status": "success",
        "message": f"Device '{device_name}' disconnected from bus '{bus_name}'.",
        "results": current_details
    }), 200


@app.route('/reset_simulation', methods=['POST'])
def reset_simulation_endpoint():
    global circuit
    # Re-initializing the circuit object also clears the stored devices
    circuit = OpenDSSCircuit("")
    circuit.solve_power_flow()
    current_details = get_current_state_details(circuit)
    save_state_to_file(current_details, "latest_api_results.txt")
    return jsonify({"status": "success", "message": "Circuit has been reset.", "results": current_details})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
