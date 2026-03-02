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
