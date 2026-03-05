FROM python:3.11-slim

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY groovebot/ groovebot/

# Run as non-root user
RUN useradd -m -u 1000 groovebot
USER groovebot

CMD ["python", "-m", "groovebot.main"]
