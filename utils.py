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
        "dfp_registry": circuit.get_all_dfp_details(),
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
        "neighborhood_details": circuit.neighborhood_data,
        "bus_details": buses_df.to_dict(orient='records')
    }

def save_management_log_to_file(management_log: list, filename: str, results_dir: str):
    filepath = os.path.join(results_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"{'='*120}\nDETAILED MANAGEMENT LOG\n{'='*120}\n")
        if management_log:
            f.write("\n".join(management_log))
        else:
            f.write("- No management actions were logged.")
    print(f"Detailed log saved to file: {filepath}")

def save_state_to_file(state_details: dict, filename: str, results_dir: str):
    """Formats and saves the current detailed state summary to a text file."""
    filepath = os.path.join(results_dir, filename)
    output = []
    
    # --- Helper function for formatting summary sections ---
    def format_section(title, content_dict):
        lines = [f"\n{'='*25} {title.upper()} {'='*25}"]
        max_key_len = max(len(k) for k in content_dict.keys()) if content_dict else 0
        for key, value in content_dict.items():
            lines.append(f"{key:<{max_key_len}} : {value}")
        return lines

    # 1. Header
    output.append(f"GRID SIMULATION STATE REPORT")
    output.append(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # 2. Critical Transformers Section
    output.append(f"\n{'='*25} CRITICAL & WARNING TRANSFORMERS {'='*25}")
    critical_transformers_found = []
    for bus in state_details.get('bus_details', []):
        for xfmr in bus.get('Transformers', []):
            if xfmr and xfmr.get('status') in ["Critical", "Warning", "Overloaded"]:
                critical_transformers_found.append(
                    f"  - Transformer '{xfmr['name']}' on Bus '{bus['Bus']}': "
                    f"Status: {xfmr['status']}, Loading: {xfmr['loading_percent']:.2f}% ({xfmr['current_kVA']:.2f}/{xfmr['rated_kVA']:.2f} kVA)"
                )
    if critical_transformers_found:
        output.extend(sorted(critical_transformers_found))
    else:
        output.append("  - All transformer loading levels are normal.")

    # 3. Power and Voltage Summaries
    output.extend(format_section("Power Summary", state_details.get('power_summary', {})))
    output.extend(format_section("Voltage Profile", state_details.get('voltage_profile', {})))

    # 4. Detailed Neighborhood Breakdown
    output.append(f"\n\n{'='*25} DETAILED NEIGHBORHOOD & NODE BREAKDOWN {'='*25}")
    
    neighborhoods = state_details.get('neighborhood_details', {})
    bus_details_list = state_details.get('bus_details', [])
    bus_map = {bus['Bus']: bus for bus in bus_details_list}
    dfp_registry = state_details.get('dfp_registry', [])

    if not neighborhoods or not bus_map:
        output.append("  - No neighborhood or bus data available.")
    else:
        for hood_id, bus_names in sorted(neighborhoods.items()):
            output.append(f"\n{'-'*20} Neighborhood: {hood_id} {'-'*20}")
            
            table_data = []
            headers = ["Bus", "VMag (pu)", "Load (kW)", "Gen (kW)", "Net (kW)", "Subscribed DFPs", "Components"]

            for bus_name in sorted(bus_names):
                bus = bus_map.get(bus_name.lower())
                if not bus:
                    continue
                
                # Format subscribed DFP names into a single string
                dfp_names = [dfp_registry[i]['name'] for i, sub in enumerate(bus.get('DFPs', [])) if sub == 1 and i < len(dfp_registry)]
                dfp_str = ", ".join(dfp_names) if dfp_names else "None"

                # Format all components into a single summary string
                comp_parts = []
                if bus.get('Transformers'):
                    for xfmr in bus['Transformers']:
                        comp_parts.append(f"XFMR:'{xfmr['name']}'({xfmr['status']},{xfmr['loading_percent']:.1f}%)")
                if bus.get('Devices'):
                    for device in bus['Devices']:
                        comp_parts.append(f"DEV:'{device['device_name']}'({device['kw']:.1f}kW)")
                if bus.get('StorageDevices'):
                    for storage in bus['StorageDevices']:
                        energy_percent = (storage['current_energy_kwh'] / storage['max_capacity_kwh'] * 100) if storage['max_capacity_kwh'] > 0 else 0
                        comp_parts.append(f"STOR:'{storage['device_name']}'({storage['mode']},{energy_percent:.1f}%)")
                comp_str = " | ".join(comp_parts) if comp_parts else "None"

                table_data.append([
                    bus['Bus'], f"{bus['VMag_pu']:.4f}", f"{bus['Load_kW']:.2f}",
                    f"{bus['Gen_kW']:.2f}", f"{bus['Net_Power_kW']:.2f}", dfp_str, comp_str
                ])

            if not table_data:
                output.append("  No bus data to display for this neighborhood.")
                continue

            # Dynamically calculate column widths based on content
            col_widths = [len(h) for h in headers]
            for row in table_data:
                for i, cell in enumerate(row):
                    col_widths[i] = max(col_widths[i], len(cell))
            
            # Create and add the formatted table to the output
            header_line = " | ".join([f"{h:<{w}}" for h, w in zip(headers, col_widths)])
            separator = "+-" + "-+-".join(["-"*w for w in col_widths]) + "-+"
            
            output.append(separator)
            output.append(f"| {header_line} |")
            output.append(separator)
            
            for row in table_data:
                row_line = " | ".join([f"{cell:<{w}}" for cell, w in zip(row, col_widths)])
                output.append(f"| {row_line} |")
            output.append(separator)

    # 5. Write the entire report to the file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("\n".join(output))

    print(f"Detailed simulation state report saved to: {filepath}")

def save_critical_transformers_report(state_details: dict, filename: str, results_dir: str):
    """Saves a dedicated report of transformers in a 'Warning', 'Critical', or 'Overloaded' state."""
    filepath = os.path.join(results_dir, filename)
    output = []

    # Report Header
    output.append(f"CRITICAL & WARNING TRANSFORMER REPORT")
    output.append(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    output.append("="*55)

    # Create a reverse map to easily find a bus's neighborhood ID
    neighborhoods = state_details.get('neighborhood_details', {})
    bus_to_hood_map = {
        bus_name.lower(): hood_id
        for hood_id, bus_list in neighborhoods.items()
        for bus_name in bus_list
    }

    critical_list = []
    # Iterate through all buses to find and format relevant transformers
    for bus in state_details.get('bus_details', []):
        bus_name_lower = bus.get('Bus', '').lower()
        for xfmr in bus.get('Transformers', []):
            if xfmr and xfmr.get('status') in ["Critical", "Warning", "Overloaded"]:
                hood_id = bus_to_hood_map.get(bus_name_lower, "N/A")
                details = (
                    f"\n- Neighborhood: {hood_id}\n"
                    f"  Bus: {bus.get('Bus', 'N/A')}\n"
                    f"  Transformer: {xfmr.get('name', 'N/A')}\n"
                    f"  Status: {xfmr.get('status', 'N/A')}\n"
                    f"  Rated Capacity: {xfmr.get('rated_kVA', 0):.2f} kVA\n"
                    f"  Current Load: {xfmr.get('current_kVA', 0):.2f} kVA\n"
                    f"  Percent of Capacity: {xfmr.get('loading_percent', 0):.2f} %"
                )
                critical_list.append(details)

    if critical_list:
        output.extend(critical_list)
    else:
        output.append("\nNo transformers are in a critical or warning state.")

    # Write the formatted report to the file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write("\n".join(output))

    print(f"Critical transformers report saved to: {filepath}")
    
def save_dfp_registry_to_file(circuit, filename: str, results_dir: str):
    filepath = os.path.join(results_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"{'='*120}\nDEMAND FLEXIBILITY PROGRAM (DFP) REGISTRY\n{'='*120}\n")
        if circuit.dfps:
            header = f"{'Index':<10}{'Name':<30}{'Description':<50}{'Min Power (kW)':<20}{'Target PF':<15}{'Registered At':<25}"
            f.write(header + "\n" + "-" * len(header) + "\n")
            for dfp in circuit.dfps:
                f.write(f"{dfp.get('index', ''):<10}{dfp.get('name', ''):<30}{dfp.get('description', ''):<50}{dfp.get('min_power_kw', 0):<20.2f}{dfp.get('target_pf', 0):<15.2f}{dfp.get('registered_at', ''):<25}\n")
        else:
            f.write("- No DFPs are currently registered.")
    print(f"DFP registry saved to file: {filepath}")

def log_dfp_activity(message: str, results_dir: str):
    filepath = os.path.join(results_dir, "dfps_logs.txt")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(filepath, 'a', encoding='utf-8') as f:
        f.write(f"[{timestamp}] {message}\n")
    print(f"DFP activity logged: {message}")

def check_and_report_critical_transformers(state_details: dict, results_dir: str, critical_api_endpoint: str):
    """
    Checks for transformers with a status other than 'OK' and sends their details to a specified API endpoint.
    """
    bus_list = state_details.get('bus_details', [])
    if not bus_list:
        return

    # Collect all transformers whose status is not "OK"
    non_ok_transformers = []
    for bus_info in bus_list:
        for transformer in bus_info.get('Transformers', []):
            if transformer and transformer.get('status') != 'OK':
                # Add the bus name to the transformer's details for context
                report_details = transformer.copy()
                report_details['bus'] = bus_info.get('Bus')
                non_ok_transformers.append(report_details)

    # If there are any non-OK transformers, send the alert
    if not non_ok_transformers:
        return

    try:
        # The payload is the list of all transformers that are not in an "OK" state
        response = requests.post(critical_api_endpoint, json=non_ok_transformers, timeout=5)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        print(f"Successfully sent details of {len(non_ok_transformers)} non-OK transformers to {critical_api_endpoint}.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending critical transformer alert to {critical_api_endpoint}: {e}")
