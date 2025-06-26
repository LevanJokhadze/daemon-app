from flask import Flask
from env import Env
import os

def create_app(config_class=Env):
    """Creates and configures an instance of the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure the main server directory exists on startup
    os.makedirs(app.config['SERVERS_BASE_PATH'], exist_ok=True)
    
    # Import and register the routes (blueprints) here
    from . import routes
    app.register_blueprint(routes.bp)

    return app