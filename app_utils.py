from flask import request, jsonify, current_app, Blueprint
from functools import wraps
import jsonschema
import os
import json
import importlib
import logging

logger = logging.getLogger(__name__)

def validate_payload(schema):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.json:
                return jsonify({"message": "Missing JSON in request"}), 400
            validation_data = request.json.copy()
            validation_data.pop('_cloud_job_id', None)
            validation_data.pop('disable_cloud_job', None)
            try:
                jsonschema.validate(instance=validation_data, schema=schema)
            except jsonschema.exceptions.ValidationError as validation_error:
                return jsonify({"message": f"Invalid payload: {validation_error.message}"}), 400
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def log_job_status(job_id, data):
    jobs_dir = os.path.join(os.getenv('LOCAL_STORAGE_PATH', '/tmp'), 'jobs')
    os.makedirs(jobs_dir, exist_ok=True)
    with open(os.path.join(jobs_dir, f"{job_id}.json"), 'w') as f:
        json.dump(data, f, indent=2)

def discover_and_register_blueprints(app):
    routes_dir = os.path.dirname(os.path.abspath(__file__)) + "/routes"
    registered = 0
    for root, _, files in os.walk(routes_dir):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                rel_path = os.path.relpath(os.path.join(root, file), routes_dir).replace(os.sep, ".")[:-3]
                full_module = f"routes.{rel_path}"
                try:
                    mod = importlib.import_module(full_module)
                    if hasattr(mod, "bp") and isinstance(mod.bp, Blueprint):
                        app.register_blueprint(mod.bp)
                        logger.info(f"Registered: {full_module}")
                        registered += 1
                except Exception as e:
                    if any(x in str(e).lower() for x in ["google", "whisper", "playwright", "yt_dlp", "boto3"]):
                        logger.debug(f"Skipped {full_module} (missing dep)")
                        continue
                    logger.warning(f"Failed {full_module}: {type(e).__name__}")
    logger.info(f"Successfully registered {registered} blueprints")
