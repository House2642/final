FROM python:3.11-slim

# Install ffmpeg for WMA → MP3 conversion
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source
COPY app.py .
COPY templates/ templates/
COPY static/ static/
COPY data/ data/

# Copy audio files and convert WMA → MP3
# The MUSIC 150 FINAL folder lives next to this Dockerfile in the repo root
COPY ["MUSIC 150 FINAL/", "/app/source_audio/"]

RUN mkdir -p /app/audio && \
    # Convert all WMA files to MP3
    for f in /app/source_audio/*.wma; do \
        [ -f "$f" ] || continue; \
        base="$(basename "$f" .wma)"; \
        ffmpeg -y -i "$f" -codec:a libmp3lame -qscale:a 2 "/app/audio/${base}.mp3" 2>/dev/null; \
    done && \
    # Copy existing MP3 files as-is
    find /app/source_audio -maxdepth 1 -iname "*.mp3" -exec cp {} /app/audio/ \; && \
    # Remove source audio to save space
    rm -rf /app/source_audio

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "60", "app:app"]
