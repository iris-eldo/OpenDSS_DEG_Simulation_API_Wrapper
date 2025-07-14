from flask import Blueprint, request, jsonify

def create_utility_blueprint(circuit_ref, run_and_update_state, log_dfp_activity, save_dfp_registry_to_file, results_dir):
    utility_bp = Blueprint('utility_bp', __name__)

    # API 1: get grid details
    @utility_bp.route('/get_node_data', methods=['GET'])
    def get_node_data_endpoint():
        current_details = run_and_update_state()
        return jsonify({"status": "success", "results": current_details}), 200

    # Get household details -> RENAMED
    @utility_bp.route('/get_node_details', methods=['POST'])
    def get_bus_details_endpoint():
        data = request.get_json()
        bus_details = circuit_ref['instance'].get_single_bus_details(str(data['bus_name']))
        if not bus_details:
            return jsonify({"status": "not_found", "message": f"Node '{data['bus_name']}' not found."}), 404
        return jsonify({"status": "success", "results": bus_details}), 200
    
    @utility_bp.route('/modify_load_neighbourhood', methods=['POST'])
    def modify_load_neighbourhood_endpoint():
        data = request.get_json()
        result = circuit_ref['instance'].modify_loads_in_neighborhood(int(data['neighbourhood']), float(data['factor']))
        if result.get("status") == "not_found":
            return jsonify(result), 404
        run_and_update_state()
        return jsonify(result), 200

    # API 4: modify load household -> RENAMED
    @utility_bp.route('/modify_load_node', methods=['POST'])
    def modify_load_household_endpoint():
        data = request.get_json()
        result = circuit_ref['instance'].modify_loads_in_houses(str(data['bus_name']), float(data['factor']))
        if result.get("status") == "success":
            run_and_update_state()
        return jsonify(result), 200

    # API 6: create dfp
    @utility_bp.route('/register_dfp', methods=['POST'])
    def register_dfp_endpoint():
        data = request.get_json()
        details = circuit_ref['instance'].register_dfp(data['name'], data['description'], data['min_power_kw'], data['target_pf'])
        save_dfp_registry_to_file(circuit_ref['instance'], "dfp_registry.txt", results_dir)
        log_dfp_activity(f"CREATED: DFP '{data['name']}'.", results_dir)
        return jsonify({"status": "success", "dfp_details": details}), 201

    # API 8: modify dfp
    @utility_bp.route('/update_dfp', methods=['PUT'])
    def update_dfp_endpoint():
        data = request.get_json()
        result = circuit_ref['instance'].update_dfp(data['name'], data['min_power_kw'], data['target_pf'], data.get('description'))
        if result.get("status") == "success":
            save_dfp_registry_to_file(circuit_ref['instance'], "dfp_registry.txt", results_dir)
            log_dfp_activity(f"MODIFIED: DFP '{data['name']}'.", results_dir)
            return jsonify(result), 200
        return jsonify(result), 404
        
    # API 9: execute dfp
    @utility_bp.route('/execute_dfp', methods=['POST'])
    def execute_dfp_endpoint():
        data = request.get_json()
        result = circuit_ref['instance'].execute_dfp(str(data['dfp_name']))
        run_and_update_state()
        log_dfp_activity(f"EXECUTION: DFP '{data['dfp_name']}'.", results_dir)
        if 'participation_data' in result:
            del result['participation_data']
        return jsonify(result), 200

    # API 11: delete dfp
    @utility_bp.route('/delete_dfp', methods=['DELETE'])
    def delete_dfp_endpoint():
        data = request.get_json()
        result = circuit_ref['instance'].delete_dfp(str(data['name']))
        if result.get("status") == "success":
            save_dfp_registry_to_file(circuit_ref['instance'], "dfp_registry.txt", results_dir)
            log_dfp_activity(f"DELETED: DFP '{data['name']}'.", results_dir)
            run_and_update_state()
            return jsonify(result), 200
        return jsonify(result), 404

    # API 18: add new household (already /add_node)
    @utility_bp.route('/add_node', methods=['POST'])
    def add_node_endpoint():
        data = request.get_json()
        result = circuit_ref['instance'].add_node(
            data['bus_name'], data['neighborhood_id'], data['coordinates'], 
            data['connections'], data['load_kw'], data.get('load_kvar', 0.0)
        )
        if result.get("status") != "success": return jsonify(result), 400
        run_and_update_state()
        return jsonify(result), 201

    # API 21: modify household (already /modify_node)
    @utility_bp.route('/modify_node', methods=['POST'])
    def modify_node_endpoint():
        data = request.get_json()
        result = circuit_ref['instance'].modify_node(data['bus_name'], data.get('load_kw'), data.get('load_kvar'))
        if result.get("status") != "success": return jsonify(result), 400
        run_and_update_state()
        return jsonify(result), 200

    # API 22: delete household (already /delete_node)
    @utility_bp.route('/delete_node', methods=['POST'])
    def delete_node_endpoint():
        data = request.get_json()
        result = circuit_ref['instance'].delete_node(data['bus_name'])
        if result.get("status") != "success": return jsonify(result), 400
        run_and_update_state()
        return jsonify(result), 200

    # API 23: get dfp details
    @utility_bp.route('/get_dfp_details', methods=['GET'])
    def get_dfp_details_endpoint():
        dfp_details = circuit_ref['instance'].get_all_dfp_details()
        return jsonify({"status": "success", "dfps": dfp_details}), 200

    # API 24: send dfp to neighborhood
    @utility_bp.route('/send_dfp_to_neighbourhood', methods=['POST'])
    def send_dfp_to_neighbourhood_endpoint():
        data = request.get_json()
        result = circuit_ref['instance'].send_dfp_to_neighbourhood(int(data['neighbourhood']), str(data['dfp_name']))
        if result.get("status") != "success": return jsonify(result), 400
        log_dfp_activity(result.get('message'), results_dir)
        run_and_update_state()
        return jsonify(result), 200

    return utility_bp