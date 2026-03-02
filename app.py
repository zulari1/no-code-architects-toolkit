# Copyright (c) 2025 Stephen G. Pope – modified for minimal faceless video use on Railway/Render
# Removed GCP, queueing, logging, webhook – kept only core Flask + blueprint registration

from flask import Flask, jsonify
import os
from app_utils import discover_and_register_blueprints  # Keep this – it loads your video/image routes

def create_app():
    app = Flask(__name__)

    # === Simple health check – required for Railway/Render to mark service healthy ===
    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({
            "status": "healthy",
            "message": "NCA Video Toolkit running (minimal mode)",
            "uptime": os.getenv("RAILWAY_UPTIME", "unknown")
        }), 200

    # === Root route for basic ping / debugging ===
    @app.route('/', methods=['GET'])
    def root():
        return jsonify({
            "status": "ok",
            "message": "Welcome to Minimal NCA Toolkit – video/image processing API",
            "endpoints": "/health (GET), /v1/... (your video routes)"
        }), 200

    # Register all video, image, media blueprints from services/
    discover_and_register_blueprints(app)

    return app

# Create and export the app instance
app = create_app()

if __name__ == '__main__':
    # For local testing only
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
