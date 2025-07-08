import os
from flask import Blueprint, json, request, jsonify, current_app, abort
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
    
@bp.route('/server/<server_id>', methods=['DELETE'])
def delete_server_route(server_id):
    """
    Handles the API request to delete a server.
    """
    if not server_id:
        return jsonify({"error": "Missing 'server_id' in URL."}), 400
    
    try:
        result = server_manager.delete_server(
            server_id,
            current_app.config['SERVERS_BASE_PATH']
        )
        return jsonify(result), 200 # 200 OK is standard for a successful DELETE
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404 # 404 Not Found is appropriate
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500
    
@bp.route('/server/<server_id>/config', methods=['PUT'])
def update_server_config(server_id: str, base_path: str, new_config: dict) -> dict:
    """
    Updates a server's conf.json file with new configuration data.
    The server should be stopped before calling this function for changes to take effect on next start.

    Args:
        server_id: The unique ID of the server to update.
        base_path: The root directory where servers are stored.
        new_config: A dictionary representing the new conf.json content.

    Returns: A dictionary with the status.
    Raises: FileNotFoundError if the server directory or conf.json does not exist.
            ValueError if new_config is not a valid dictionary.
            RuntimeError on file write errors.
    """
    if not isinstance(new_config, dict):
        raise ValueError("Provided configuration is not a valid dictionary.")

    server_path = os.path.join(base_path, server_id)
    conf_path = os.path.join(server_path, 'conf.json')

    if not os.path.isdir(server_path):
        raise FileNotFoundError(f"Server directory '{server_id}' not found.")
    
    if not os.path.exists(conf_path):
        raise FileNotFoundError(f"Configuration file 'conf.json' not found for server '{server_id}'.")

    try:
        print(f"Updating configuration for server '{server_id}'.")
        # Overwrite the entire file with the new configuration.
        # indent=4 makes the JSON file human-readable.
        with open(conf_path, 'w') as f:
            json.dump(new_config, f, indent=4)
            
    except Exception as e:
        # Catch potential file permission errors or other issues.
        raise RuntimeError(f"Failed to write to conf.json for server '{server_id}': {e}")

    return {"status": "config_updated"}