FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for yt-dlp
RUN sed -i 's|http://|https://|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY groovebot/ groovebot/

# Run as non-root user
RUN useradd -m -u 1000 groovebot
USER groovebot

CMD ["python", "-m", "groovebot.main"]
