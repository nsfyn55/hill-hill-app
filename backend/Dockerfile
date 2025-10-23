FROM python:3.11-slim

WORKDIR /app

# Copy requirements first for better caching
COPY src/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code (this will be overridden by volume in development)
COPY src/ .

# Expose the Flask port
EXPOSE 5000

# Use gunicorn for production, flask dev server for development
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--reload", "app:app"]

