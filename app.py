from flask import Flask, jsonify
import os
from app_utils import discover_and_register_blueprints

def create_app():
    app = Flask(__name__)

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({"status": "healthy", "message": "NCA Toolkit - Faceless Video Mode"}), 200

    @app.route('/', methods=['GET'])
    def root():
        return jsonify({"status": "ok", "message": "Minimal NCA Toolkit for Faceless YouTube"}), 200

    discover_and_register_blueprints(app)
    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
