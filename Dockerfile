# Use a lightweight Python base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Install required system dependencies, including Docker CLI for sandboxing
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Set up workspace
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Run the chatbot
CMD ["python", "/app/src/aura.py"]
