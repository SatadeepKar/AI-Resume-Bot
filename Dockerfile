FROM python:3.10-slim

# Install system dependencies for wkhtmltopdf and headless rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    wkhtmltopdf \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy application files
COPY . .

# Install Python requirements
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8000 (standard for local, overridden by Render's $PORT)
EXPOSE 8000

# Default command is to run the multi-process supervisor entrypoint
CMD ["python", "entrypoint.py"]