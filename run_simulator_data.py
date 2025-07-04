import os
import pandas as pd
from flask import Flask, request, jsonify
from main import OpenDSSCircuit

# --- Global Application Setup ---
app = Flask(__name__)
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results_api')
os.makedirs(RESULTS_DIR, exist_ok=True)

print("--- Initializing Global OpenDSS Circuit with Automated Management ---")
circuit = OpenDSSCircuit("") 
management_status = circuit.solve_and_manage_loading() 
print(f"--- Initial Baseline Simulation Complete. Status: {management_status.get('status')} ---")


def get_current_state_details(circuit_object: OpenDSSCircuit, management_status: dict) -> dict:
    """Helper function to gather results and include the management status."""
    pf_results = circuit_object.get_power_flow_results()
    buses_df = circuit_object.get_buses_with_loads()
    
    total_load_kw = sum(v.get('load_kw', 0) for v in circuit_object.bus_capacities.values())
    
    return {
        "management_status": management_status,
        "power_summary": {
            "converged": pf_results['converged'],
            "total_circuit_power_kW": round(pf_results['total_power_kW'], 2),
            "total_losses_kW": round(pf_results['total_losses_kW'], 4),
            "total_load_kW": round(total_load_kw, 2),
        },
        "voltage_profile": {
            "min_voltage_pu": round(buses_df['VMag_pu'].min(), 4) if not buses_df.empty else 0,
            "max_voltage_pu": round(buses_df['VMag_pu'].max(), 4) if not buses_df.empty else 0,
            "avg_voltage_pu": round(buses_df['VMag_pu'].mean(), 4) if not buses_df.empty else 0,
        },
        "bus_details": buses_df.to_dict(orient='records')
    }

def save_state_to_file(state_details: dict, filename: str):
    """Formats and saves the current state, including detailed transformer statuses, to a text file."""
    filepath = os.path.join(RESULTS_DIR, filename)
    management = state_details.get('management_status', {})
    summary = state_details.get('power_summary', {})
    voltage = state_details.get('voltage_profile', {})
    bus_list = state_details.get('bus_details', [])
    
    output = [f"{'='*120}\nSIMULATION STATE REPORT\n{'='*120}\n"]
    
    output.append("--- SYSTEM STATUS & MANAGEMENT LOG ---")
    output.append(f"Overall Status: {management.get('status', 'N/A')}")
    if management.get('management_log'):
        for log_entry in management['management_log']:
            output.append(f"- {log_entry}")
    output.append("\n")

    output.append("--- POWER SUMMARY ---")
    output.append(f"Converged: {summary.get('converged')}")
    output.append(f"Total Circuit Power (from grid): {summary.get('total_circuit_power_kW'):.2f} kW")
    output.append(f"Total True Load: {summary.get('total_load_kW'):.2f} kW")
    output.append(f"Total Losses: {summary.get('total_losses_kW'):.2f} kW\n")
    
    output.append("--- VOLTAGE PROFILE ---")
    output.append(f"Min/Avg/Max Voltage (p.u.): {voltage.get('min_voltage_pu'):.4f} / {voltage.get('avg_voltage_pu'):.4f} / {voltage.get('max_voltage_pu'):.4f}\n")

    output.append("--- DETAILED BUS & NODE DATA ---")
    header = f"{'Bus':<10}{'Node':<5}{'VMag (pu)':<15}{'VAngle (deg)':<15}{'Load (kW)':<15}{'Gen (kW)':<15}{'Net (kW)':<15}"
    output.append(header)
    output.append("-" * len(header))
    
    processed_buses = set()
    for bus_info in bus_list:
        bus_name = bus_info.get('Bus', '')
        if bus_name not in processed_buses:
            bus_nodes = [b for b in bus_list if b['Bus'] == bus_name]
            total_load = bus_nodes[0].get('Load_kW', 0) * len(bus_nodes)
            total_gen = bus_nodes[0].get('Gen_kW', 0) * len(bus_nodes)
            total_net = bus_nodes[0].get('Net_Power_kW', 0) * len(bus_nodes)
            
            output.append(f"{bus_name:<10}{'--':<5}{bus_nodes[0].get('VMag_pu', 0):<15.4f}{bus_nodes[0].get('VAngle', 0):<15.2f}{total_load:<15.2f}{total_gen:<15.2f}{total_net:<15.2f}")
            processed_buses.add(bus_name)

            # Display attached transformers with their detailed status
            if bus_nodes[0].get('Transformers'):
                for xfmr in bus_nodes[0]['Transformers']:
                    if xfmr: # Check if transformer object is valid
                        status_line = f"Status: {xfmr.get('status')} ({xfmr.get('loading_percent')}%)"
                        rating_line = f"Rating: {xfmr.get('rated_kVA')} kVA"
                        output.append(f"  -> {'Transformer:':<15} {xfmr.get('name'):<25} {status_line:<25} {rating_line}")

            # Display attached devices
            if bus_nodes[0].get('Devices'):
                for device in bus_nodes[0]['Devices']:
                    output.append(f"  -> {'Device:':<15} {device.get('device_name', ''):<25} {device.get('kw', 0):>10.2f} kW")

    with open(filepath, 'w', encoding='utf-8') as f: f.write("\n".join(output))
    print(f"Results updated in file: {filepath}")


# --- API Endpoints ---
@app.route('/modify_load_neighbourhood', methods=['POST'])
def modify_load_neighbourhood_endpoint():
    data = request.get_json()
    try:
        neighbourhood, factor = int(data['neighbourhood']), float(data['factor'])
    except (TypeError, KeyError, ValueError):
        return jsonify({"status": "error", "message": "Invalid payload."}), 400
    
    circuit.modify_loads_in_neighborhood(neighbourhood, factor)
    management_status = circuit.solve_and_manage_loading()
    
    current_details = get_current_state_details(circuit, management_status)
    save_state_to_file(current_details, "latest_api_results.txt")
    return jsonify({"status": "success", "results": current_details}), 200

@app.route('/modify_load_household', methods=['POST'])
def modify_load_household_endpoint():
    data = request.get_json()
    try:
        bus_name, factor = str(data['bus_name']), float(data['factor'])
    except (TypeError, KeyError, ValueError):
        return jsonify({"status": "error", "message": "Invalid payload."}), 400

    result = circuit.modify_loads_in_houses(bus_name, factor)
    if result.get("status") != "success":
         return jsonify(result), 404 if "not found" in result.get("message", "") else 200

    management_status = circuit.solve_and_manage_loading()
    current_details = get_current_state_details(circuit, management_status)
    save_state_to_file(current_details, "latest_api_results.txt")
    return jsonify({"status": "success", "results": current_details}), 200

@app.route('/add_generator', methods=['POST'])
def add_generator_endpoint():
    data = request.get_json()
    try:
        bus_name, kw, phases = str(data['bus_name']), float(data['kw']), int(data.get('phases', 1))
    except (TypeError, KeyError, ValueError):
        return jsonify({"status": "error", "message": "Invalid payload."}), 400
    
    circuit.add_generation_to_bus(bus_name, kw, phases)
    management_status = circuit.solve_and_manage_loading()
    current_details = get_current_state_details(circuit, management_status)
    save_state_to_file(current_details, "latest_api_results.txt")
    return jsonify({"status": "success", "results": current_details}), 200

@app.route('/add_device', methods=['POST'])
def add_device_endpoint():
    data = request.get_json()
    try:
        bus_name, device_name, kw, phases = str(data['bus_name']), str(data['device_name']), float(data['kw']), int(data.get('phases', 1))
    except (TypeError, KeyError, ValueError):
        return jsonify({"status": "error", "message": "Invalid payload."}), 400
    
    circuit.add_device_to_bus(bus_name, device_name, kw, phases)
    management_status = circuit.solve_and_manage_loading()
    current_details = get_current_state_details(circuit, management_status)
    save_state_to_file(current_details, "latest_api_results.txt")
    return jsonify({"status": "success", "results": current_details}), 200

@app.route('/disconnect_device', methods=['POST'])
def disconnect_device_endpoint():
    data = request.get_json()
    try:
        bus_name, device_name = str(data['bus_name']), str(data['device_name'])
    except (TypeError, KeyError, ValueError):
        return jsonify({"status": "error", "message": "Invalid payload."}), 400

    if not circuit.disconnect_device_from_bus(bus_name, device_name):
        return jsonify({"status": "not_found", "message": f"Device not found."}), 404

    management_status = circuit.solve_and_manage_loading()
    current_details = get_current_state_details(circuit, management_status)
    save_state_to_file(current_details, "latest_api_results.txt")
    return jsonify({"status": "success", "results": current_details}), 200

@app.route('/reset_simulation', methods=['POST'])
def reset_simulation_endpoint():
    global circuit
    print("--- Resetting Simulation ---")
    circuit = OpenDSSCircuit("")
    management_status = circuit.solve_and_manage_loading()
    current_details = get_current_state_details(circuit, management_status)
    save_state_to_file(current_details, "latest_api_results.txt")
    return jsonify({"status": "success", "message": "Circuit reset and stabilized.", "results": current_details})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)