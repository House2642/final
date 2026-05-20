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

# Copy all media files (audio + video)
COPY ["MUSIC 150 FINAL/", "/app/MUSIC 150 FINAL/"]

# Convert WMA → MP3 for audio serving
RUN mkdir -p /app/audio && \
    # Convert standard .wma files
    for f in "/app/MUSIC 150 FINAL/"*.wma; do \
        [ -f "$f" ] || continue; \
        base="$(basename "$f" .wma)"; \
        ffmpeg -y -i "$f" -codec:a libmp3lame -qscale:a 2 "/app/audio/${base}.mp3" 2>/dev/null; \
    done && \
    # Convert non-standard WMA files: "Name_wma" or "Name wma" (no dot extension)
    for f in "/app/MUSIC 150 FINAL/"*_wma "/app/MUSIC 150 FINAL/"*" wma"; do \
        [ -f "$f" ] || continue; \
        base="$(basename "$f")"; \
        name="${base%_wma}"; name="${name% wma}"; \
        ffmpeg -y -i "$f" -codec:a libmp3lame -qscale:a 2 "/app/audio/${name}.mp3" 2>/dev/null; \
    done && \
    # Copy existing MP3 files as-is
    find "/app/MUSIC 150 FINAL" -maxdepth 1 -iname "*.mp3" -exec cp {} /app/audio/ \;

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--timeout", "60", "app:app"]
