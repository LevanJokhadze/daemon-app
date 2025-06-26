# orion-daemon/app/services/server_manager.py

import os
import subprocess
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