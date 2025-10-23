#!/bin/bash

# Development run script for Podman
# This script builds and runs the Flask app with volume mapping

set -e

echo "Building Flask app container..."
podman build -t flask-app:latest .

echo "Starting Flask app with volume mapping..."
podman run --rm -it \
  --name flask-app-dev \
  -p 5001:5000 \
  -v ./src:/app:z \
  -e FLASK_ENV=development \
  -e JWT_SECRET_KEY=${JWT_SECRET_KEY:-dev-secret-key-change-in-production} \
  flask-app:latest \
  flask run --host=0.0.0.0 --port=5000 --reload

