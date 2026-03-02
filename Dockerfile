# ====================== MINIMAL BASE FOR RENDER ======================
FROM python:3.12-slim

# Install only what's needed for FFmpeg + subtitles + fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libass9 \
    fonts-liberation \
    fontconfig \
    libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

# Copy your custom fonts (create a ./fonts folder in your repo with .ttf files)
COPY ./fonts /usr/share/fonts/custom
RUN fc-cache -f -v

# Set working directory
WORKDIR /app

# Copy requirements first (cache optimization for Render)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt gunicorn

# Copy the rest of your app code
COPY . .

# Create startup script (same as your original but simpler)
RUN echo '#!/bin/bash\n\
gunicorn --bind 0.0.0.0:8080 \
    --workers ${GUNICORN_WORKERS:-2} \
    --timeout ${GUNICORN_TIMEOUT:-300} \
    --worker-class sync \
    app:app' > /app/run_gunicorn.sh && \
    chmod +x /app/run_gunicorn.sh

# Expose port (Render default)
EXPOSE 8080

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    GUNICORN_WORKERS=2 \
    GUNICORN_TIMEOUT=300

# Start the API
CMD ["/app/run_gunicorn.sh"]
