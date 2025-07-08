# orion-daemon/app/services/server_manager.py

import os
import subprocess
import zipfile
import shutil
from flask import json
import psutil

# A simple in-memory dictionary to act as our "database" of running servers.
# Key: server_id (e.g., "server_abc")
# Value: The subprocess.Popen object for that server's process.
_running_servers = {}

def start_server(server_id: str, base_path: str, executable_name: str) -> dict:
    """
    Starts a game server process for a given server_id.

    Returns: A dictionary with status and process information.
    Raises: FileNotFoundError if server directory or executable is not found.
            ValueError if server is already running.
    """

    if server_id in _running_servers and _running_servers[server_id].poll() is None:
        raise ValueError(f"Server '{server_id}' is already running.")

    server_path = os.path.join(base_path, server_id)
    executable_path = os.path.join(server_path, executable_name)
    log_path = os.path.join(server_path, 'console.log')

    if not os.path.isdir(server_path):
        raise FileNotFoundError(f"Server directory not found: {server_path}")
    if not os.path.isfile(executable_path):
        raise FileNotFoundError(f"Server executable not found: {executable_path}")

    # Open the log file in write mode, which will clear old logs on start.
    log_file = open(log_path, "w")

    # Start the server process. We run it from its own directory (cwd).
    # stderr=subprocess.STDOUT redirects error output to the same log file.
    process = subprocess.Popen(
        [executable_path], 
        cwd=server_path, 
        stdout=log_file, 
        stderr=subprocess.STDOUT
    )

    _running_servers[server_id] = process
    return {"status": "started", "pid": process.pid}

def stop_server(server_id: str) -> dict:
    """Stops a running game server process."""
    if server_id not in _running_servers or _running_servers[server_id].poll() is not None:
        raise ValueError(f"Server '{server_id}' is not running.")
    
    process = _running_servers[server_id]
    process.terminate()  # Sends a SIGTERM signal for a graceful shutdown.
    process.wait(timeout=10) # Wait up to 10 seconds for it to close.
    
    del _running_servers[server_id]
    return {"status": "stopped"}

def get_server_status(server_id: str) -> dict:
    """Gets the status and resource usage of a server."""
    if server_id not in _running_servers or _running_servers[server_id].poll() is not None:
        return {"status": "stopped", "cpu": 0, "memory": 0}

    try:
        p = psutil.Process(_running_servers[server_id].pid)
        with p.oneshot(): # Efficiently gets multiple stats at once
            return {
                "status": "running",
                "cpu": p.cpu_percent(interval=0.1),
                "memory": p.memory_info().rss / (1024 * 1024),  # In MB
                "pid": p.pid
            }
    except psutil.NoSuchProcess:
        # The process died without us knowing, clean it up.
        del _running_servers[server_id]
        return {"status": "stopped", "cpu": 0, "memory": 0}

def get_server_logs(server_id: str, base_path: str, lines: int = 100) -> str:
    """Reads the last N lines from a server's console.log file."""
    log_path = os.path.join(base_path, server_id, 'console.log')
    if not os.path.exists(log_path):
        raise FileNotFoundError("Log file not found.")

    with open(log_path, "r") as f:
        # Use a deque for efficient reading of last N lines, but this is simpler
        log_lines = f.readlines()
        return "".join(log_lines[-lines:])
    
def create_server(server_id: str, base_path: str, templates_path: str, template_name: str) -> dict:
    """
    Creates a new server directory by copying a pre-existing local template.
    
    Args:
        server_id: The unique ID for the new server.
        base_path: The root directory where servers are stored.
        templates_path: The directory where master templates are stored.
        template_name: The filename of the template to use (e.g., "default.zip").
    
    Returns: A dictionary with the status.
    Raises: ValueError, FileNotFoundError
    """
    server_path = os.path.join(base_path, server_id)
    
    # Ensure the template name is safe and doesn't allow path traversal (e.g., ../../)
    if '..' in template_name or '/' in template_name:
        raise ValueError("Invalid template name.")

    template_zip_path = os.path.join(templates_path, template_name)

    if os.path.isdir(server_path):
        raise ValueError(f"Server directory '{server_id}' already exists.")

    if not os.path.isfile(template_zip_path):
        raise FileNotFoundError(f"Template '{template_name}' not found at {template_zip_path}")

    print(f"Creating new server '{server_id}' using template '{template_name}'")
    os.makedirs(server_path)

    with zipfile.ZipFile(template_zip_path, 'r') as zip_ref:
        zip_ref.extractall(server_path)

    # Make the server executable
    executable_path = os.path.join(server_path, 'ragemp-server')
    if os.path.exists(executable_path):
        os.chmod(executable_path, 0o755)

    print(f"Successfully created server '{server_id}'.")
    return {"status": "created", "path": server_path}

def delete_server(server_id: str, base_path: str) -> dict:
    """
    Deletes a server's files and directory.
    It will first attempt to stop the server if it is running.

    Args:
        server_id: The unique ID of the server to delete.
        base_path: The root directory where servers are stored.

    Returns: A dictionary with the status.
    Raises: FileNotFoundError if the server directory does not exist.
    """
    # First, check if the server is running and stop it if it is.
    # This prevents errors from trying to delete files that are in use.
    if server_id in _running_servers and _running_servers[server_id].poll() is None:
        print(f"Server '{server_id}' is running. Attempting to stop it before deletion.")
        stop_server(server_id)

    server_path = os.path.join(base_path, server_id)

    if not os.path.isdir(server_path):
        raise FileNotFoundError(f"Server directory '{server_id}' not found. Cannot delete.")

    # Use shutil.rmtree to recursively delete the directory and all its contents.
    # This is powerful and dangerous, so we've made sure the path is correct.
    print(f"Deleting server directory: {server_path}")
    shutil.rmtree(server_path)
    
    # If the server was in our tracking dictionary for any reason, remove it.
    if server_id in _running_servers:
        del _running_servers[server_id]

    print(f"Successfully deleted server '{server_id}'.")
    return {"status": "deleted"}

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