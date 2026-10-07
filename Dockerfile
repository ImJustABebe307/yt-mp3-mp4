FROM python:3.11-slim
# Install ffmpeg for trimming + faster downloads
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Koyeb sets PORT=8000 automatically
CMD ["python", "final_goat_v9_cloud_24_7.py"]
