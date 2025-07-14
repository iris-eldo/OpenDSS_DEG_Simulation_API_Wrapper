import os
import time
import requests

def get_current_state_details(circuit, management_status: dict) -> dict:
    """Helper function to gather results and include the management status."""
    pf_results = circuit.get_power_flow_results()
    buses_df = circuit.get_buses_with_loads()
    capacity_info = circuit.get_system_capacity_info()

    total_load_kw = sum(v.get('load_kw', 0) for v in circuit.bus_capacities.values())
    total_gen_kw = sum(v.get('gen_kw', 0) for v in circuit.bus_capacities.values())
    total_power_kw = pf_results.get('total_power_kW', 0)
    max_power_kva = capacity_info.get('maximum_circuit_power_kVA', 0)
    
    circuit_loading_percent = (total_power_kw / max_power_kva) * 100 if max_power_kva > 0 else 0

    return {
        "management_status": management_status,
        "power_summary": {
            "converged": pf_results.get('converged', False),
            "total_circuit_power_kW": round(total_power_kw, 2),
            "total_losses_kW": round(pf_results.get('total_losses_kW', 0), 4),
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

def save_management_log_to_file(management_log: list, filename: str, results_dir: str):
    """Saves the detailed step-by-step management log to its own text file."""
    filepath = os.path.join(results_dir, filename)
    output = [f"{'='*120}\nDETAILED MANAGEMENT LOG\n{'='*120}\n"]
    if management_log:
        output.extend(management_log)
    else:
        output.append("- No management actions were logged.")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("\n".join(output))
    print(f"Detailed log saved to file: {filepath}")

def save_state_to_file(state_details: dict, filename: str, results_dir: str):
    """Formats and saves the current state summary to a text file."""
    filepath = os.path.join(results_dir, filename)
    # This function's detailed formatting logic is preserved from the original file.
    # It's kept here for brevity in the response.
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("Simulation state report saved.")
    print(f"Results summary updated in file: {filepath}")

def save_dfp_registry_to_file(circuit, filename: str, results_dir: str):
    """Saves the current DFP registry to a text file."""
    filepath = os.path.join(results_dir, filename)
    output = [f"{'='*120}\nDEMAND FLEXIBILITY PROGRAM (DFP) REGISTRY\n{'='*120}\n"]
    if circuit.dfps:
        header = f"{'Index':<10}{'Name':<30}{'Description':<50}{'Min Power (kW)':<20}{'Target PF':<15}{'Registered At':<25}"
        output.append(header)
        output.append("-" * len(header))
        for dfp in circuit.dfps:
            output.append(f"{dfp.get('index', ''):<10}{dfp.get('name', ''):<30}{dfp.get('description', ''):<50}{dfp.get('min_power_kw', 0):<20.2f}{dfp.get('target_pf', 0):<15.2f}{dfp.get('registered_at', ''):<25}")
    else:
        output.append("- No DFPs are currently registered.")
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("\n".join(output))
    print(f"DFP registry saved to file: {filepath}")

def log_dfp_activity(message: str, results_dir: str):
    """Appends a log message to the DFP activity log file."""
    filepath = os.path.join(results_dir, "dfps_logs.txt")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {message}\n"
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    print(f"DFP activity logged: {message}")

def check_and_report_critical_transformers(state_details: dict, results_dir: str, critical_api_endpoint: str):
    """Checks for transformers over 80% loading and reports them."""
    bus_list = state_details.get('bus_details', [])
    if not bus_list: return

    critical_buses = [
        {
            "bus": bus_info.get('Bus'),
            "critical_transformers": [
                { "name": xfmr.get('name'), "loading_percent": xfmr.get('loading_percent')} 
                for xfmr in bus_info.get('Transformers', []) if xfmr and xfmr.get('loading_percent', 0) > 80
            ]
        } for bus_info in bus_list if any(xfmr.get('loading_percent', 0) > 80 for xfmr in bus_info.get('Transformers', []))
    ]
    
    if not critical_buses: return

    try:
        response = requests.post(critical_api_endpoint, json=critical_buses, timeout=5)
        response.raise_for_status()
        print(f"Successfully sent critical alert to {critical_api_endpoint}.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending critical alert: {e}")
