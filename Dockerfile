FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libass9 fontconfig && rm -rf /var/lib/apt/lists/*

COPY fonts /usr/share/fonts/custom
RUN fc-cache -f -v

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .
RUN echo '#!/bin/bash\ngunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 300 app:app' > run.sh && chmod +x run.sh

EXPOSE 8080
CMD ["./run.sh"]
