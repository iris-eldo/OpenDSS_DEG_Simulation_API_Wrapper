import os
import pickle
import zipfile
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from main import OpenDSSCircuit

def create_dashboard_blueprint(circuit_ref, run_and_update_state, test_systems_dir, cache_dir):
    dashboard_bp = Blueprint('dashboard_bp', __name__)

    # API 16: upload zip file
    @dashboard_bp.route('/upload_test_system', methods=['POST'])
    def upload_test_system():
        if 'file' not in request.files: return jsonify({"message": "No file part"}), 400
        file = request.files['file']
        if file.filename == '': return jsonify({"message": "No selected file"}), 400
        if file and file.filename.endswith('.zip'):
            filename = secure_filename(file.filename)
            zip_path = os.path.join(test_systems_dir, filename)
            file.save(zip_path)
            try:
                extract_path = os.path.join(test_systems_dir, os.path.splitext(filename)[0])
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                os.remove(zip_path)
                return jsonify({"status": "success", "message": f"Uploaded '{filename}'."}), 200
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500
        return jsonify({"message": "Invalid file type"}), 400

    # API 17: switch test system
    @dashboard_bp.route('/switch_active_system', methods=['POST'])
    def switch_active_system():
        data = request.get_json()
        system_name = data['system_name']
        master_file_path = os.path.join(test_systems_dir, system_name, 'Master.dss')
        if not os.path.exists(master_file_path):
            return jsonify({"message": f"Master.dss not found for system '{system_name}'."}), 404
        try:
            circuit_ref['instance'] = OpenDSSCircuit(master_file_path)
            current_details = run_and_update_state()
            return jsonify({"status": "success", "message": f"Switched to {system_name}", "results": current_details}), 200
        except Exception as e:
            circuit_ref['instance'] = OpenDSSCircuit("") # Revert on failure
            run_and_update_state()
            return jsonify({"status": "error", "message": str(e)}), 500

    # API 19: save cache
    @dashboard_bp.route('/save_cache', methods=['POST'])
    def save_cache_endpoint():
        data = request.get_json()
        filename = str(data['filename'])
        if not filename.endswith('.cache'): filename += '.cache'
        cache_path = os.path.join(cache_dir, secure_filename(filename))
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(circuit_ref['instance'].get_state(), f)
            return jsonify({"status": "success", "message": f"Saved state to '{filename}'."}), 200
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

    # API 20: load cache
    @dashboard_bp.route('/load_cache', methods=['POST'])
    def load_cache_endpoint():
        data = request.get_json()
        filename = str(data['filename'])
        if not filename.endswith('.cache'): filename += '.cache'
        cache_path = os.path.join(cache_dir, secure_filename(filename))
        if not os.path.exists(cache_path):
            return jsonify({"message": f"Cache file '{filename}' not found."}), 404
        try:
            with open(cache_path, 'rb') as f:
                loaded_state = pickle.load(f)
            
            base_dss_file = loaded_state.get("dss_file")
            circuit_ref['instance'] = OpenDSSCircuit(base_dss_file)
            circuit_ref['instance'].set_state(loaded_state)
            
            current_details = run_and_update_state()
            return jsonify({"status": "success", "message": f"Loaded state from '{filename}'.", "results": current_details}), 200
        except Exception as e:
            circuit_ref['instance'] = OpenDSSCircuit("") # Revert on failure
            run_and_update_state()
            return jsonify({"status": "error", "message": str(e)}), 500

    return dashboard_bp