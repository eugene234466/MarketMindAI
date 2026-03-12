import os
from flask import Flask
from config import Config


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
        static_folder=os.path.join(os.path.dirname(__file__), "static"),
    )

    app.config.from_object(Config)

    # Ensure reports folder exists
    os.makedirs(app.config["REPORTS_FOLDER"], exist_ok=True)

    # Register routes blueprint
    from app.routes import main
    app.register_blueprint(main)

    return app
