import os
import sys
from flask import Flask

# Add the project's root directory to the Python path for correct imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from main import OpenDSSCircuit
from utils import (
    get_current_state_details, 
    save_management_log_to_file, 
    save_state_to_file,
    save_critical_transformers_report,
    save_dfp_registry_to_file,
    log_dfp_activity,
    check_and_report_critical_transformers
)
from api.utility_routes import create_utility_blueprint
from api.user_routes import create_user_blueprint
from api.dashboard_routes import create_dashboard_blueprint

# --- Global Application Setup ---
app = Flask(__name__)

# Define directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, 'results_api')
TEST_SYSTEMS_DIR = os.path.join(BASE_DIR, 'Test_Systems')
CACHE_DIR = os.path.join(BASE_DIR, 'cache')
os.makedirs(RESULTS_DIR, exist_ok=True)
os.makedirs(TEST_SYSTEMS_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)
CRITICAL_API_ENDPOINT = "http://localhost:3000/api/critical"

# --- Global Circuit Initialization ---
print("--- Initializing Global OpenDSS Circuit ---")
# Use a dictionary to hold the circuit instance, making it mutable across modules
circuit_ref = {'instance': OpenDSSCircuit("")}
management_status = {'status': None}

def run_and_update_state():
    """Central function to run simulation and update all reports."""
    current_circuit = circuit_ref['instance']
    sim_status = current_circuit.solve_and_manage_loading()
    management_status['status'] = sim_status
    
    if 'management_log' in sim_status:
        save_management_log_to_file(sim_status['management_log'], "management_log.txt", RESULTS_DIR)

    current_details = get_current_state_details(current_circuit, sim_status)
    save_state_to_file(current_details, "latest_api_results.txt", RESULTS_DIR)
    # Add the call to generate critical.txt
    save_critical_transformers_report(current_details, "critical.txt", RESULTS_DIR)
    check_and_report_critical_transformers(current_details, RESULTS_DIR, CRITICAL_API_ENDPOINT)
    
    return current_details

# Run once at startup
run_and_update_state()
save_dfp_registry_to_file(circuit_ref['instance'], "dfp_registry.txt", RESULTS_DIR)
print("--- Initial Baseline Simulation Complete ---")

# --- Register Blueprints ---
utility_bp = create_utility_blueprint(circuit_ref, run_and_update_state, log_dfp_activity, save_dfp_registry_to_file, RESULTS_DIR)
user_bp = create_user_blueprint(circuit_ref, run_and_update_state, log_dfp_activity, RESULTS_DIR)
dashboard_bp = create_dashboard_blueprint(circuit_ref, run_and_update_state, TEST_SYSTEMS_DIR, CACHE_DIR)

app.register_blueprint(utility_bp)
app.register_blueprint(user_bp)
app.register_blueprint(dashboard_bp)

# --- Main Execution ---
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
