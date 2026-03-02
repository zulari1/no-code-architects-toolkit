from flask import Flask, request, jsonify, send_file
import ffmpeg
import os
import tempfile
import uuid

app = Flask(__name__)

# ====================== HEALTH & ROOT ======================
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "message": "Minimal Faceless Video Toolkit"}), 200

@app.route('/', methods=['GET'])
def root():
    return jsonify({"status": "ok", "message": "Faceless YouTube Toolkit - trim, caption, concat, vertical, thumbnail"}), 200

# ====================== MINIO SETUP (using your Railway env vars) ======================
s3_client = boto3.client(
    's3',
    endpoint_url=os.getenv('S3_ENDPOINT_URL'),
    aws_access_key_id=os.getenv('S3_ACCESS_KEY'),
    aws_secret_access_key=os.getenv('S3_SECRET_KEY'),
    region_name=os.getenv('S3_REGION', 'us-east-1'),
    config=Config(signature_version='s3v4')
)
BUCKET_NAME = os.getenv('S3_BUCKET_NAME', 'nca-toolkit-prod')

def upload_to_minio(file_path, object_name):
    try:
        s3_client.upload_file(file_path, BUCKET_NAME, object_name)
        # Return public URL (adjust domain if you have custom MINIO_DOMAIN)
        return f"https://{BUCKET_NAME}.railway.internal/{object_name}"
    except Exception as e:
        return f"Upload failed: {str(e)}"

# ====================== HEALTH & ROOT ======================
@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy", "message": "Faceless Video Toolkit - All Features Ready"}), 200

@app.route('/', methods=['GET'])
def root():
    return jsonify({"status": "ok", "message": "All endpoints working"}), 200

# ====================== IMAGE TO VIDEO (your requested endpoint) ======================
@app.route('/v1/image/to_video', methods=['POST'])
def image_to_video():
    data = request.json or {}
    image_url = data.get('image_url')
    duration = float(data.get('duration', 20))
    zoom_speed = float(data.get('zoom_speed', 6))

    if not image_url and 'file' not in request.files:
        return jsonify({"error": "image_url or file is required"}), 400

    # Download or save file
    if image_url:
        try:
            r = requests.get(image_url, timeout=15, stream=True)
            r.raise_for_status()
            ext = image_url.split('.')[-1].lower()
            input_path = f"/tmp/img_{uuid.uuid4()}.{ext}"
            with open(input_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        except Exception as e:
            return jsonify({"error": f"Failed to download image: {str(e)}"}), 400
    else:
        file = request.files['file']
        filename = secure_filename(file.filename)
        input_path = os.path.join('/tmp', filename)
        file.save(input_path)

    output_filename = f"anim_{uuid.uuid4()}.mp4"
    output_path = f"/tmp/{output_filename}"

    try:
        stream = ffmpeg.input(input_path, loop=1, t=duration)
        stream = ffmpeg.filter(stream, 'zoompan', z=f'zoom+0.00{zoom_speed}', d=125, x='iw/2-(iw/zoom/2)', y='ih/2-(ih/zoom/2)', s='1080x1920')
        stream = ffmpeg.output(stream, output_path, vcodec='libx264', pix_fmt='yuv420p', r=30)
        ffmpeg.run(stream, overwrite_output=True)
    except ffmpeg.Error as e:
        if os.path.exists(input_path): os.remove(input_path)
        return jsonify({"error": str(e.stderr.decode())}), 500

    # Upload to MinIO and return URL
    video_url = upload_to_minio(output_path, output_filename)
    if os.path.exists(input_path): os.remove(input_path)
    if os.path.exists(output_path): os.remove(output_path)

    return jsonify({
        "video_url": video_url,
        "duration": duration,
        "id": data.get("id", "Scene 1")
    }), 200
    
# ====================== CORE ENDPOINTS ======================

# 1. Trim video
@app.route('/v1/video/trim', methods=['POST'])
def trim_video():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['file']
    start = request.form.get('start', 0)
    duration = request.form.get('duration', 60)
    
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_in:
        file.save(tmp_in.name)
        tmp_in_path = tmp_in.name
    
    output_path = f"/tmp/{uuid.uuid4()}.mp4"
    
    stream = ffmpeg.input(tmp_in_path, ss=start, t=duration)
    stream = ffmpeg.output(stream, output_path, c='copy')
    ffmpeg.run(stream, overwrite_output=True)
    
    os.unlink(tmp_in_path)
    return send_file(output_path, as_attachment=True, download_name="trimmed.mp4")

# 2. Burn captions (simple text or .srt support)
@app.route('/v1/video/caption_video', methods=['POST'])
def caption_video():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['file']
    text = request.form.get('text', 'Your caption here')
    
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_in:
        file.save(tmp_in.name)
        tmp_in_path = tmp_in.name
    
    output_path = f"/tmp/{uuid.uuid4()}.mp4"
    
    stream = ffmpeg.input(tmp_in_path)
    stream = ffmpeg.drawtext(stream, text=text, fontsize=48, fontcolor='white', x='(w-text_w)/2', y='h-100', shadowcolor='black', shadowx=2, shadowy=2)
    stream = ffmpeg.output(stream, output_path, c='copy')
    ffmpeg.run(stream, overwrite_output=True)
    
    os.unlink(tmp_in_path)
    return send_file(output_path, as_attachment=True, download_name="captioned.mp4")

# 3. Concatenate multiple clips (send multiple files)
@app.route('/v1/video/concatenate', methods=['POST'])
def concatenate():
    files = request.files.getlist('files')
    if not files:
        return jsonify({"error": "No files uploaded"}), 400
    
    inputs = []
    for f in files:
        tmp = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
        f.save(tmp.name)
        inputs.append(tmp.name)
    
    output_path = f"/tmp/{uuid.uuid4()}.mp4"
    concat_list = "file '" + "'\nfile '".join(inputs) + "'"
    
    with open("/tmp/concat.txt", "w") as f:
        f.write(concat_list)
    
    stream = ffmpeg.input("/tmp/concat.txt", format='concat', safe=0)
    stream = ffmpeg.output(stream, output_path, c='copy')
    ffmpeg.run(stream, overwrite_output=True)
    
    for p in inputs:
        os.unlink(p)
    os.unlink("/tmp/concat.txt")
    
    return send_file(output_path, as_attachment=True, download_name="concatenated.mp4")

# 4. Vertical crop for Shorts (9:16)
@app.route('/v1/video/vertical', methods=['POST'])
def vertical_crop():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['file']
    
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_in:
        file.save(tmp_in.name)
        tmp_in_path = tmp_in.name
    
    output_path = f"/tmp/{uuid.uuid4()}.mp4"
    
    stream = ffmpeg.input(tmp_in_path)
    stream = ffmpeg.filter(stream, 'crop', 'ih*9/16', 'ih')
    stream = ffmpeg.filter(stream, 'scale', 1080, 1920)
    stream = ffmpeg.output(stream, output_path)
    ffmpeg.run(stream, overwrite_output=True)
    
    os.unlink(tmp_in_path)
    return send_file(output_path, as_attachment=True, download_name="vertical_short.mp4")


# 5. Thumbnail from video
@app.route('/v1/video/thumbnail', methods=['POST'])
def thumbnail():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['file']
    
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_in:
        file.save(tmp_in.name)
        tmp_in_path = tmp_in.name
    
    output_path = f"/tmp/{uuid.uuid4()}.jpg"
    stream = ffmpeg.input(tmp_in_path, ss=2)
    stream = ffmpeg.output(stream, output_path, vframes=1)
    ffmpeg.run(stream, overwrite_output=True)
    
    os.unlink(tmp_in_path)
    return send_file(output_path, as_attachment=True, download_name="thumbnail.jpg")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)
