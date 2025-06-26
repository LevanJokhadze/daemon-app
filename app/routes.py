from flask import Blueprint, request, jsonify, current_app, abort
from .services import server_manager

# A Blueprint is a way to organize a group of related views and other code.
bp = Blueprint('api', __name__, url_prefix='/api')

# --- Middleware for Security ---
# This runs before every request to this blueprint.
@bp.before_request
def check_api_key():
    api_key = current_app.config['API_KEY']
    if request.headers.get('X-Api-Key') != api_key:
        abort(401, description="Invalid or missing API Key.") # Unauthorized

# --- Server Action Routes ---

@bp.route('/server/start', methods=['POST'])
def start_server_route():
    data = request.get_json()
    if not data or 'server_id' not in data:
        return jsonify({"error": "Missing 'server_id' in request body."}), 400
    
    try:
        result = server_manager.start_server(
            data['server_id'],
            current_app.config['SERVERS_BASE_PATH'],
            current_app.config['SERVER_EXECUTABLE_NAME']
        )
        return jsonify(result), 200
    except (ValueError, FileNotFoundError) as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@bp.route('/server/stop', methods=['POST'])
def stop_server_route():
    data = request.get_json()
    if not data or 'server_id' not in data:
        return jsonify({"error": "Missing 'server_id' in request body."}), 400

    try:
        result = server_manager.stop_server(data['server_id'])
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

@bp.route('/server/<server_id>/status', methods=['GET'])
def get_status_route(server_id):
    result = server_manager.get_server_status(server_id)
    return jsonify(result), 200

@bp.route('/server/<server_id>/logs', methods=['GET'])
def get_logs_route(server_id):
    try:
        logs = server_manager.get_server_logs(
            server_id, 
            current_app.config['SERVERS_BASE_PATH']
        )
        return jsonify({"logs": logs}), 200
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404

@bp.route('/server/create', methods=['POST'])
def create_server_route():
    data = request.get_json()
    if not data or 'server_id' not in data:
        return jsonify({"error": "Missing 'server_id' in request body."}), 400

    # We can provide a default template or make it required.
    template_name = data.get('template_name', 'default.zip')

    try:
        result = server_manager.create_server(
            server_id=data['server_id'],
            base_path=current_app.config['SERVERS_BASE_PATH'],
            templates_path=current_app.config['TEMPLATES_PATH'],
            template_name=template_name
        )
        return jsonify(result), 201 # 201 Created
    except (ValueError, FileNotFoundError) as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500