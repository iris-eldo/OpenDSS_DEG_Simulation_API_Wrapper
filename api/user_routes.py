from flask import Blueprint, request, jsonify

def create_user_blueprint(circuit_ref, run_and_update_state, log_dfp_activity, results_dir):
    user_bp = Blueprint('user_bp', __name__)

    # API 2: add generator
    @user_bp.route('/add_generator', methods=['POST'])
    def add_generator_endpoint():
        data = request.get_json()
        result = circuit_ref['instance'].add_generation_to_bus(str(data['bus_name']), float(data['kw']), int(data.get('phases', 1)))
        if result.get("status") != "success": return jsonify(result), 400
        run_and_update_state()
        return jsonify(result), 201

    # API 5: add device
    @user_bp.route('/add_device', methods=['POST'])
    def add_device_endpoint():
        data = request.get_json()
        result = circuit_ref['instance'].add_device_to_bus(str(data['bus_name']), str(data['device_name']), float(data['kw']), int(data.get('phases', 1)))
        if result.get("status") != "success": return jsonify(result), 400
        run_and_update_state()
        return jsonify(result), 201

    # API 7: subscribe dfp
    @user_bp.route('/subscribe_dfp', methods=['POST'])
    def subscribe_dfp_endpoint():
        data = request.get_json()
        result = circuit_ref['instance'].subscribe_dfp(str(data['bus_name']), str(data['dfp_name']))
        if result.get("status") != "success": return jsonify(result), 400
        log_dfp_activity(f"SUBSCRIBED: Bus '{data['bus_name']}' to DFP '{data['dfp_name']}'.", results_dir)
        run_and_update_state()
        return jsonify(result), 200

    # API 10: unsubscribe dfp
    @user_bp.route('/unsubscribe_dfp', methods=['POST'])
    def unsubscribe_dfp_endpoint():
        data = request.get_json()
        result = circuit_ref['instance'].unsubscribe_dfp(str(data['bus_name']), str(data['dfp_name']))
        if result.get("status") != "success": return jsonify(result), 400
        log_dfp_activity(f"UNSUBSCRIBED: Bus '{data['bus_name']}' from DFP '{data['dfp_name']}'.", results_dir)
        run_and_update_state()
        return jsonify(result), 200

    # API 12: modify load device -> RENAMED
    @user_bp.route('/modify_devices_in_node', methods=['POST'])
    def modify_devices_in_bus_endpoint():
        data = request.get_json()
        result = circuit_ref['instance'].modify_high_wattage_devices_in_bus(str(data['bus_name']), float(data['power_threshold_kw']), float(data['reduction_factor']))
        run_and_update_state()
        log_dfp_activity(f"DEVICE_MODIFICATION: on node '{data['bus_name']}'.", results_dir)
        return jsonify(result), 200

    # API 13: disconnect device
    @user_bp.route('/disconnect_device', methods=['POST'])
    def disconnect_device_endpoint():
        data = request.get_json()
        result = circuit_ref['instance'].disconnect_device_from_bus(str(data['bus_name']), str(data['device_name']))
        if result.get("status") != "success": return jsonify(result), 404
        run_and_update_state()
        return jsonify(result), 200

    # API 14: add storage
    @user_bp.route('/add_storage_device', methods=['POST'])
    def add_storage_device_endpoint():
        data = request.get_json()
        result = circuit_ref['instance'].add_storage_device(data['bus_name'], data['device_name'], data['max_capacity_kwh'], data['charge_rate_kw'], data['discharge_rate_kw'])
        if result.get("status") != "success": return jsonify(result), 400
        run_and_update_state()
        return jsonify(result), 201

    # API 15: toggle storage
    @user_bp.route('/toggle_storage_device', methods=['POST'])
    def toggle_storage_device_endpoint():
        data = request.get_json()
        result = circuit_ref['instance'].toggle_storage_device(str(data['device_name']), str(data.get('action', 'toggle')))
        if result.get("status") != "success": return jsonify(result), 400
        run_and_update_state()
        return jsonify(result), 200

    return user_bp