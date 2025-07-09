import os
import pandas as pd
from flask import Flask, request, jsonify
from main import OpenDSSCircuit
import time
import requests

# --- Global Application Setup ---
app = Flask(__name__)
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'results_api')
os.makedirs(RESULTS_DIR, exist_ok=True)

# The endpoint for sending critical transformer alerts.
CRITICAL_API_ENDPOINT = "http://localhost:3000/api/critical"

print("--- Initializing Global OpenDSS Circuit with Automated Management ---")
circuit = OpenDSSCircuit("")
management_status = circuit.solve_and_manage_loading()
print(f"--- Initial Baseline Simulation Complete. Status: {management_status.get('status')} ---")


def get_current_state_details(circuit_object: OpenDSSCircuit, management_status: dict) -> dict:
    """Helper function to gather results and include the management status."""
    pf_results = circuit_object.get_power_flow_results()
    buses_df = circuit_object.get_buses_with_loads()
    capacity_info = circuit_object.get_system_capacity_info()

    total_load_kw = sum(v.get('load_kw', 0) for v in circuit_object.bus_capacities.values())
    total_gen_kw = sum(v.get('gen_kw', 0) for v in circuit_object.bus_capacities.values())
    total_power_kw = pf_results['total_power_kW']
    max_power_kva = capacity_info.get('maximum_circuit_power_kVA', 0)
    
    # Calculate loading percentage based on total transformer capacity
    circuit_loading_percent = 0
    if max_power_kva > 0:
        circuit_loading_percent = (total_power_kw / max_power_kva) * 100

    return {
        "management_status": management_status,
        "power_summary": {
            "converged": pf_results['converged'],
            "total_circuit_power_kW": round(total_power_kw, 2),
            "total_losses_kW": round(pf_results['total_losses_kW'], 4),
            "total_load_kW": round(total_load_kw, 2),
            "total_gen_kW": round(total_gen_kw, 2),
            "maximum_circuit_power_kVA": round(max_power_kva, 2),
            "maximum_circuit_load_kW": round(capacity_info.get('maximum_circuit_load_kW', 0), 2),
            "circuit_loading_percent": round(circuit_loading_percent, 2)
        },
        "voltage_profile": {
            "min_voltage_pu": round(buses_df['VMag_pu'].min(), 4) if not buses_df.empty else 0,
            "max_voltage_pu": round(buses_df['VMag_pu'].max(), 4) if not buses_df.empty else 0,
            "avg_voltage_pu": round(buses_df['VMag_pu'].mean(), 4) if not buses_df.empty else 0,
        },
        "bus_details": buses_df.to_dict(orient='records')
    }

def save_management_log_to_file(management_log: list, filename: str):
    """Saves the detailed step-by-step management log to its own text file."""
    filepath = os.path.join(RESULTS_DIR, filename)
    output = [f"{'='*120}\nDETAILED MANAGEMENT LOG\n{'='*120}\n"]

    if management_log:
        for log_entry in management_log:
            output.append(log_entry)
    else:
        output.append("- No management actions were logged.")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("\n".join(output))
    print(f"Detailed log saved to file: {filepath}")

def save_state_to_file(state_details: dict, filename: str):
    """Formats and saves the current state summary to a text file."""
    filepath = os.path.join(RESULTS_DIR, filename)
    management = state_details.get('management_status', {})
    summary = state_details.get('power_summary', {})
    voltage = state_details.get('voltage_profile', {})
    bus_list = state_details.get('bus_details', [])

    output = [f"{'='*120}\nSIMULATION STATE REPORT\n{'='*120}\n"]

    output.append("--- SYSTEM STATUS & MANAGEMENT LOG ---")
    output.append(f"Overall Status: {management.get('status', 'N/A')}")
    management_log = management.get('management_log')
    if management_log:
        output.append(management_log[-1])
    output.append("\n")

    output.append("--- POWER SUMMARY ---")
    output.append(f"Converged: {summary.get('converged')}")
    output.append(f"Total Circuit Power (from grid): {summary.get('total_circuit_power_kW'):.2f} kW")
    output.append(f"Total System Load: {summary.get('total_load_kW'):.2f} kW")
    output.append(f"Total System Generation: {summary.get('total_gen_kW'):.2f} kW")
    output.append(f"Maximum Circuit Power (Capacity): {summary.get('maximum_circuit_power_kVA'):.2f} kVA")
    output.append(f"Maximum Circuit Load (Registered): {summary.get('maximum_circuit_load_kW'):.2f} kW")
    output.append(f"Circuit Loading: {summary.get('circuit_loading_percent'):.2f}%")
    output.append(f"Total Losses: {summary.get('total_losses_kW'):.2f} kW\n")

    output.append("--- VOLTAGE PROFILE ---")
    output.append(f"Min/Avg/Max Voltage (p.u.): {voltage.get('min_voltage_pu'):.4f} / {voltage.get('avg_voltage_pu'):.4f} / {voltage.get('max_voltage_pu'):.4f}\n")

    output.append("--- DETAILED BUS & NODE DATA ---")
    header = f"{'Bus':<10}{'VMag (pu)':<15}{'VAngle (deg)':<15}{'Load (kW)':<15}{'Gen (kW)':<15}{'Net (kW)':<15}"
    output.append(header)
    output.append("-" * len(header))

    processed_buses = set()
    for bus_info in bus_list:
        bus_name = bus_info.get('Bus', '')
        if bus_name not in processed_buses:
            bus_nodes = [b for b in bus_list if b['Bus'] == bus_name]
            total_load = bus_nodes[0].get('Load_kW', 0)
            total_gen = bus_nodes[0].get('Gen_kW', 0)
            total_net = bus_nodes[0].get('Net_Power_kW', 0)
            
            output.append(f"{bus_name:<10}{bus_nodes[0].get('VMag_pu', 0):<15.4f}{bus_nodes[0].get('VAngle', 0):<15.2f}{total_load:<15.2f}{total_gen:<15.2f}{total_net:<15.2f}")
            processed_buses.add(bus_name)
            
            subscribed_dfps = bus_info.get('SubscribedDFPs', [])
            if subscribed_dfps:
                output.append(f"  -> {'Subscribed DFPs:':<18}")
                for dfp in subscribed_dfps:
                    dfp_line = (f"     - Name: {dfp.get('name', 'N/A')}, "
                                f"Min Power: {dfp.get('min_power_kw', 0):.2f} kW, "
                                f"Target PF: {dfp.get('target_pf', 0):.2f}, "
                                f"Last Participation: {dfp.get('last_participation_status', 'N/A')}")
                    output.append(dfp_line)

            if bus_nodes[0].get('Transformers'):
                for xfmr in bus_nodes[0]['Transformers']:
                    if xfmr:
                        status_line = f"Status: {xfmr.get('status')} ({xfmr.get('loading_percent')}%)"
                        rating_line = f"Rating: {xfmr.get('rated_kVA')} kVA"
                        output.append(f"  -> {'Transformer:':<18} {xfmr.get('name'):<25} {status_line:<25} {rating_line}")

            if bus_nodes[0].get('Devices'):
                for device in bus_nodes[0]['Devices']:
                    output.append(f"  -> {'Device:':<18} {device.get('device_name', ''):<25} {device.get('kw', 0):>10.2f} kW")
            
            if bus_nodes[0].get('StorageDevices'):
                for storage in bus_nodes[0]['StorageDevices']:
                    if storage:
                        storage_line_1 = f"Mode: {storage.get('mode', 'N/A').upper()}"
                        storage_line_2 = f"Energy: {storage.get('current_energy_kwh', 0):.2f} / {storage.get('max_capacity_kwh', 0):.2f} kWh"
                        
                        charge_rate_str = f"{storage.get('actual_charge_rate', 0):.2f}/{storage.get('build_charge_rate', 0):.2f}"
                        discharge_rate_str = f"{storage.get('actual_discharge_rate', 0):.2f}/{storage.get('build_discharge_rate', 0):.2f}"
                        storage_line_3 = f"Rates C(Act/Bld): {charge_rate_str} kW | D(Act/Bld): {discharge_rate_str} kW"

                        output.append(f"  -> {'Storage:':<18} {storage.get('device_name', ''):<25} {storage_line_1:<25} {storage_line_2}")
                        output.append(f"  -> {'':<18} {'':<25} {storage_line_3}")


    with open(filepath, 'w', encoding='utf-8') as f: f.write("\n".join(output))
    print(f"Results summary updated in file: {filepath}")

def save_dfp_registry_to_file(circuit_object: OpenDSSCircuit, filename: str):
    """Saves the current DFP registry to a text file."""
    filepath = os.path.join(RESULTS_DIR, filename)
    output = [f"{'='*120}\nDEMAND FLEXIBILITY PROGRAM (DFP) REGISTRY\n{'='*120}\n"]

    if circuit_object.dfps:
        header = f"{'Index':<10}{'Name':<30}{'Min Power (kW)':<20}{'Target PF':<15}{'Registered At':<25}"
        output.append(header)
        output.append("-" * len(header))
        for dfp in circuit_object.dfps:
            output.append(f"{dfp['index']:<10}{dfp['name']:<30}{dfp['min_power_kw']:<20.2f}{dfp['target_pf']:<15.2f}{dfp['registered_at']:<25}")
    else:
        output.append("- No DFPs are currently registered.")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("\n".join(output))
    print(f"DFP registry saved to file: {filepath}")

def log_dfp_activity(message: str):
    """Appends a log message to the DFP activity log file."""
    filepath = os.path.join(RESULTS_DIR, "dfps_logs.txt")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    print(f"DFP activity logged: {message}")

def check_and_report_critical_transformers(state_details: dict):
    """
    Checks for transformers over 80% loading, writes them to critical.txt,
    and sends a POST request to a critical alert API.
    """
    bus_list = state_details.get('bus_details', [])
    if not bus_list:
        return

    critical_buses = []
    for bus_info in bus_list:
        transformers = bus_info.get('Transformers', [])
        if not transformers:
            continue

        critical_transformers_on_bus = []
        for xfmr in transformers:
            if xfmr and xfmr.get('loading_percent', 0) > 80:
                critical_transformers_on_bus.append({
                    "name": xfmr.get('name'),
                    "loading_percent": xfmr.get('loading_percent'),
                    "rated_kVA": xfmr.get('rated_kVA'),
                    "current_kVA": xfmr.get('current_kVA')
                })
        
        if critical_transformers_on_bus:
            critical_buses.append({
                "bus": bus_info.get('Bus'),
                "critical_transformers": critical_transformers_on_bus
            })

    filepath = os.path.join(RESULTS_DIR, "critical.txt")
    if not critical_buses:
        if os.path.exists(filepath):
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] All transformers are operating within normal limits (<80% capacity).\n")
        return

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    output = [
        f"CRITICAL TRANSFORMER REPORT - {timestamp}",
        "=" * 40,
        ""
    ]
    for bus_data in critical_buses:
        output.append(f"Bus: {bus_data['bus']}")
        for xfmr in bus_data['critical_transformers']:
            output.append(f"  - Transformer: {xfmr['name']}")
            output.append(f"    - Loading: {xfmr['loading_percent']}%")
            output.append(f"    - Rated kVA: {xfmr['rated_kVA']}")
            output.append(f"    - Current kVA: {xfmr['current_kVA']}\n")

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("\n".join(output))
    print(f"CRITICAL: High-load transformer report saved to: {filepath}")

    try:
        response = requests.post(CRITICAL_API_ENDPOINT, json=critical_buses, timeout=5)
        response.raise_for_status()
        print(f"Successfully sent critical alert {critical_buses} to {CRITICAL_API_ENDPOINT}. Status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error sending critical alert {critical_buses} to {CRITICAL_API_ENDPOINT}: {e}")


# --- Combined State Update and Reporting Function ---
def run_and_update_state():
    """
    Runs the simulation, gets the state, and saves all reports.
    Returns the current state details for the API response.
    """
    global management_status
    management_status = circuit.solve_and_manage_loading()

    if 'management_log' in management_status:
        save_management_log_to_file(management_status['management_log'], "management_log.txt")

    current_details = get_current_state_details(circuit, management_status)
    save_state_to_file(current_details, "latest_api_results.txt")
    
    check_and_report_critical_transformers(current_details)
    
    return current_details

# Save the initial state files after the first run
initial_details = run_and_update_state()
save_dfp_registry_to_file(circuit, "dfp_registry.txt")


# --- API Endpoints ---
@app.route('/get_node_data', methods=['GET'])
def get_node_data_endpoint():
    """
    Runs a new simulation and returns all bus data.
    """
    current_details = run_and_update_state()
    return jsonify({"status": "success", "results": current_details}), 200

@app.route('/modify_load_neighbourhood', methods=['POST'])
def modify_load_neighbourhood_endpoint():
    data = request.get_json()
    try:
        neighbourhood, factor = int(data['neighbourhood']), float(data['factor'])
    except (TypeError, KeyError, ValueError):
        return jsonify({"status": "error", "message": "Invalid payload."}), 400

    circuit.modify_loads_in_neighborhood(neighbourhood, factor)
    current_details = run_and_update_state()
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

    current_details = run_and_update_state()
    return jsonify({"status": "success", "results": current_details}), 200

@app.route('/add_generator', methods=['POST'])
def add_generator_endpoint():
    data = request.get_json()
    try:
        bus_name, kw, phases = str(data['bus_name']), float(data['kw']), int(data.get('phases', 1))
    except (TypeError, KeyError, ValueError):
        return jsonify({"status": "error", "message": "Invalid payload."}), 400

    circuit.add_generation_to_bus(bus_name, kw, phases)
    current_details = run_and_update_state()
    return jsonify({"status": "success", "results": current_details}), 200

@app.route('/add_device', methods=['POST'])
def add_device_endpoint():
    data = request.get_json()
    try:
        bus_name, device_name, kw, phases = str(data['bus_name']), str(data['device_name']), float(data['kw']), int(data.get('phases', 1))
    except (TypeError, KeyError, ValueError):
        return jsonify({"status": "error", "message": "Invalid payload."}), 400

    circuit.add_device_to_bus(bus_name, device_name, kw, phases)
    current_details = run_and_update_state()
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

    current_details = run_and_update_state()
    return jsonify({"status": "success", "results": current_details}), 200

# --- Storage Device API Endpoints ---

@app.route('/add_storage_device', methods=['POST'])
def add_storage_device_endpoint():
    data = request.get_json()
    try:
        bus_name = str(data['bus_name'])
        device_name = str(data['device_name'])
        max_capacity_kwh = float(data['max_capacity_kwh'])
        charge_rate_kw = float(data['charge_rate_kw'])
        discharge_rate_kw = float(data['discharge_rate_kw'])
    except (TypeError, KeyError, ValueError) as e:
        return jsonify({"status": "error", "message": f"Invalid payload. Required: bus_name, device_name, max_capacity_kwh, charge_rate_kw, discharge_rate_kw. Error: {e}"}), 400

    circuit.add_storage_device(bus_name, device_name, max_capacity_kwh, charge_rate_kw, discharge_rate_kw)
    current_details = run_and_update_state()
    return jsonify({"status": "success", "message": f"Storage device '{device_name}' added.", "results": current_details}), 200

@app.route('/toggle_storage_device', methods=['POST'])
def toggle_storage_device_endpoint():
    data = request.get_json()
    try:
        bus_name = str(data['bus_name'])
        device_name = str(data['device_name'])
        action = str(data.get('action', 'toggle')).lower()
        if action not in ['toggle', 'disconnect']:
            return jsonify({"status": "error", "message": "Invalid action. Must be 'toggle' or 'disconnect'."}), 400
    except (TypeError, KeyError, ValueError):
        return jsonify({"status": "error", "message": "Invalid payload. Required: 'bus_name' (string), 'device_name' (string) and optional 'action' (string: 'toggle' or 'disconnect')."}), 400

    result = circuit.toggle_storage_device(bus_name, device_name, action)
    if result.get("status") != "success":
        if "not found" in result.get("message", "").lower():
            return jsonify(result), 404
        return jsonify(result), 400

    current_details = run_and_update_state()
    return jsonify({"status": "success", "message": result['message'], "results": current_details}), 200


# --- DFP Management API Endpoints ---

@app.route('/subscribe_dfp', methods=['POST'])
def subscribe_dfp_endpoint():
    data = request.get_json()
    try:
        bus_name, dfp_name = str(data['bus_name']), str(data['dfp_name'])
    except (TypeError, KeyError, ValueError):
        return jsonify({"status": "error", "message": "Invalid payload: bus_name (string) and dfp_name (string) are required."}), 400

    result = circuit.subscribe_dfp(bus_name, dfp_name)
    if result.get("status") != "success":
         return jsonify(result), 400

    log_dfp_activity(f"SUBSCRIBED: Bus '{bus_name}' to DFP '{dfp_name}'.")
    current_details = run_and_update_state()
    return jsonify({"status": "success", "message": f"Successfully subscribed bus '{bus_name}' to DFP '{dfp_name}'.", "results": current_details}), 200

@app.route('/unsubscribe_dfp', methods=['POST'])
def unsubscribe_dfp_endpoint():
    data = request.get_json()
    try:
        bus_name, dfp_name = str(data['bus_name']), str(data['dfp_name'])
    except (TypeError, KeyError, ValueError):
        return jsonify({"status": "error", "message": "Invalid payload: bus_name (string) and dfp_name (string) are required."}), 400

    result = circuit.unsubscribe_dfp(bus_name, dfp_name)
    if result.get("status") != "success":
         return jsonify(result), 400

    log_dfp_activity(f"UNSUBSCRIBED: Bus '{bus_name}' from DFP '{dfp_name}'.")
    current_details = run_and_update_state()
    return jsonify({"status": "success", "message": f"Successfully unsubscribed bus '{bus_name}' from DFP '{dfp_name}'.", "results": current_details}), 200

@app.route('/register_dfp', methods=['POST'])
def register_dfp_endpoint():
    data = request.get_json()
    try:
        dfp_name = str(data['name'])
        min_power_kw = float(data['min_power_kw'])
        target_pf = float(data['target_pf'])

        if not (0.0 < target_pf <= 1.0):
            return jsonify({"status": "error", "message": "Target Power Factor must be between 0.0 and 1.0 (exclusive of 0)."}), 400

    except (TypeError, KeyError, ValueError) as e:
        return jsonify({"status": "error", "message": f"Invalid payload. Required: 'name' (str), 'min_power_kw' (float), 'target_pf' (float). Error: {e}"}), 400

    registered_dfp = circuit.register_dfp(dfp_name, min_power_kw, target_pf)
    save_dfp_registry_to_file(circuit, "dfp_registry.txt")
    log_dfp_activity(f"CREATED: DFP '{dfp_name}' registered with details: {registered_dfp}.")

    return jsonify({
        "status": "success",
        "message": f"DFP '{dfp_name}' registered successfully with index {registered_dfp['index']}.",
        "dfp_details": registered_dfp
    }), 200

@app.route('/update_dfp', methods=['PUT'])
def update_dfp_endpoint():
    data = request.get_json()
    try:
        name = str(data['name'])
        new_min_power_kw = float(data['min_power_kw'])
        new_target_pf = float(data['target_pf'])

        if not (0.0 < new_target_pf <= 1.0):
            return jsonify({"status": "error", "message": "Target Power Factor must be between 0.0 and 1.0 (exclusive of 0)."}), 400

    except (TypeError, KeyError, ValueError):
        return jsonify({"status": "error", "message": "Invalid payload. Required: 'name' (str), 'min_power_kw' (float), 'target_pf' (float)."}), 400

    result = circuit.update_dfp(name, new_min_power_kw, new_target_pf)

    if result.get("status") == "success":
        save_dfp_registry_to_file(circuit, "dfp_registry.txt")
        log_dfp_activity(f"MODIFIED: DFP '{name}' updated. New details: {result.get('data')}.")
        return jsonify(result), 200
    else:
        return jsonify(result), 404

@app.route('/delete_dfp', methods=['DELETE'])
def delete_dfp_endpoint():
    data = request.get_json()
    try:
        name = str(data['name'])
    except (TypeError, KeyError, ValueError):
        return jsonify({"status": "error", "message": "Invalid payload. Required: 'name' (str)."}), 400

    result = circuit.delete_dfp(name)

    if result.get("status") == "success":
        save_dfp_registry_to_file(circuit, "dfp_registry.txt")
        log_dfp_activity(f"DELETED: DFP '{name}'.")
        current_details = run_and_update_state()
        return jsonify({"status": "success", "message": f"DFP '{name}' deleted successfully."}), 200
    else:
        return jsonify(result), 404

@app.route('/modify_devices_in_bus', methods=['POST'])
def modify_devices_in_bus_endpoint():
    """Reduces load for high-wattage devices on a specific bus."""
    data = request.get_json()
    try:
        bus_name = str(data['bus_name'])
        power_threshold_kw = float(data['power_threshold_kw'])
        reduction_factor = float(data['reduction_factor'])
        if not (0.0 <= reduction_factor <= 1.0):
            raise ValueError("Reduction factor must be between 0.0 and 1.0.")
    except (TypeError, KeyError, ValueError) as e:
        return jsonify({"status": "error", "message": f"Invalid payload. Error: {e}"}), 400

    circuit.modify_high_wattage_devices_in_bus(bus_name, power_threshold_kw, reduction_factor)
    current_details = run_and_update_state()
    log_dfp_activity(f"DEVICE_MODIFICATION: on bus '{bus_name}'.")

    return jsonify({"status": "success", "results": current_details}), 200


@app.route('/execute_dfp', methods=['POST'])
def execute_dfp_endpoint():
    """Executes a DFP's rules on all subscribed buses and reports on participation."""
    data = request.get_json()
    try:
        dfp_name = str(data['dfp_name'])
    except (TypeError, KeyError, ValueError):
        return jsonify({"status": "error", "message": "Invalid payload. Required: 'dfp_name' (str)."}), 400

    result = circuit.execute_dfp(dfp_name)
    
    if result.get("status") != "success":
        return jsonify(result), 404 if "not found" in result.get("message", "") else 200

    # Re-run simulation to reflect changes from DFP execution
    current_details = run_and_update_state()
    log_dfp_activity(f"EXECUTION: DFP '{dfp_name}' was run. Details: {result.get('details')}")

    return jsonify({
        "status": "success",
        "message": result.get('message'),
        "details": result.get('details'),
        "results": current_details # Return the full updated state
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
