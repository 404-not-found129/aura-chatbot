#!/bin/bash
# Script to run Aura Chatbot in a Docker virtual machine

echo "Building Aura Chatbot Docker image..."
docker build -t aura-chatbot .

echo "Starting Aura Chatbot in isolated VM..."
# We map the local directory to /app/workspace inside the container
# so it can safely read/write files in this directory.
# -it is required for the interactive prompt_toolkit interface.
# We also pass the host's docker socket so the chatbot can spawn VM sandboxes
# for running AI shell commands.
# We mount the global .env file to persist API keys.

touch .env

docker run -it --rm \
    -v "$(pwd):/app/workspace" \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v "$(pwd)/.env:/app/.env" \
    -e HOST_WORKSPACE="$(pwd)" \
    -w /app/workspace \
    aura-chatbot "$@"
