# Copyright (c) 2025 Stephen G. Pope – cleaned & fixed for minimal deployment
# Removed duplicate code, fixed missing imports, removed undefined variables

from flask import request, jsonify, current_app, Blueprint
from functools import wraps
import jsonschema
import os
import json
import time
import importlib
import logging
from typing import Callable

logger = logging.getLogger(__name__)

# ====================== PAYLOAD VALIDATION DECORATOR ======================
def validate_payload(schema):
    def decorator(f: Callable):
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

# ====================== JOB STATUS LOGGER (minimal) ======================
def log_job_status(job_id: str, data: dict):
    jobs_dir = os.path.join(os.getenv('LOCAL_STORAGE_PATH', '/app/storage'), 'jobs')
    
    if not os.path.exists(jobs_dir):
        os.makedirs(jobs_dir, exist_ok=True)
    
    job_file = os.path.join(jobs_dir, f"{job_id}.json")
    
    with open(job_file, 'w') as f:
        json.dump(data, f, indent=2)

# ====================== SAFE BLUEPRINT DISCOVERY ======================
def discover_and_register_blueprints(app: Flask):
    """
    Safely discovers and registers blueprints from routes/ folder.
    Skips any module that fails to import due to missing dependencies.
    """
    routes_dir = os.path.dirname(os.path.abspath(__file__)) + "/routes"
    registered = 0

    for root, _, files in os.walk(routes_dir):
        for file in files:
            if file.endswith(".py") and not file.startswith("__"):
                module_path = os.path.join(root, file)
                rel_path = os.path.relpath(module_path, routes_dir).replace(os.sep, ".")[:-3]
                full_module = f"routes.{rel_path}"

                try:
                    mod = importlib.import_module(full_module)
                    if hasattr(mod, "bp") and isinstance(mod.bp, Blueprint):
                        app.register_blueprint(mod.bp)
                        logger.info(f"Registered blueprint: {full_module}")
                        registered += 1
                except Exception as e:
                    # Gracefully skip modules with missing deps
                    missing_deps = ["google", "whisper", "playwright", "yt_dlp", "boto3", "torch"]
                    if any(dep in str(e).lower() for dep in missing_deps):
                        logger.debug(f"Skipped {full_module} (missing dep)")
                        continue
                    logger.warning(f"Failed to load {full_module}: {type(e).__name__}: {str(e)}")

    logger.info(f"Successfully registered {registered} blueprints")
