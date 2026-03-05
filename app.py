from flask import Flask, request, jsonify
import os
import boto3
from botocore.client import Config
from app_utils import discover_and_register_blueprints

# ====================== MINIO / S3 CLIENT (using your exact env vars) ======================
s3_client = boto3.client(
    's3',
    endpoint_url=os.getenv('S3_ENDPOINT_URL'),
    aws_access_key_id=os.getenv('S3_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('S3_SECRET_KEY'),
    region_name=os.getenv('S3_REGION', 'us-east-1'),
    config=Config(signature_version='s3v4')
)
BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'nca-toolkit-prod')

def create_app():
    app = Flask(__name__)

    # Health check (fixes Railway health check failures)
    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({"status": "healthy", "message": "NCA Toolkit Running"}), 200

    # Root (already working)
    @app.route('/', methods=['GET'])
    def root():
        return jsonify({"status": "ok", "message": "NCA Toolkit - Faceless Video Mode"}), 200

    # Register all video/image routes (safe discovery)
    discover_and_register_blueprints(app)

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
