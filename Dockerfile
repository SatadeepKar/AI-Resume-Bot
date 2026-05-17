FROM python:3.10-slim

# Install system dependencies for wkhtmltopdf and downloading assets
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    fontconfig \
    libfreetype6 \
    libjpeg62-turbo \
    libpng16-16 \
    libx11-6 \
    libxcb1 \
    libxext6 \
    libxrender1 \
    xfonts-75dpi \
    xfonts-base \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Download and install the patched wkhtmltopdf package specifically built for Debian Bookworm
RUN wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends ./wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
    && rm wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
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