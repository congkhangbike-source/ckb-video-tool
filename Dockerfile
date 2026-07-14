FROM python:3.11-slim

# Install FFmpeg and dependencies
RUN apt-get update && \
    apt-get install -y ffmpeg gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Railway sets PORT env var
ENV PORT=7860
EXPOSE 7860

CMD ["python", "web_server.py"]
