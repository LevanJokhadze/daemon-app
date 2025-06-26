import os

class Env:
    """
    Main configuration class. All config variables are defined here.
    """
    # --- SECURITY ---
    # This is the secret key your main backend must send in the 'X-Api-Key' header.
    # It's best to set this as an environment variable in production for security.
    # We provide a default value here for easy development.
    API_KEY = os.environ.get('ORION_API_KEY', 'default-super-secret-key-change-me')

    # --- PATHS ---
    # The absolute base path where all game server data will be stored.
    # Each server will have its own subdirectory inside this path.
    # Example: /home/orion/servers/server_abc/, /home/orion/servers/server_xyz/
    SERVERS_BASE_PATH = os.environ.get('ORION_SERVERS_PATH', '/var/lib/orion/servers')

    TEMPLATES_PATH = os.environ.get('ORION_TEMPLATES_PATH', '/var/lib/orion/templates')
    
    # The name of the RageMP server executable on Linux
    SERVER_EXECUTABLE_NAME = 'ragemp-server'