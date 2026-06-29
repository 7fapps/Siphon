FROM python:3.11-slim

WORKDIR /app

# Install system dependencies: FFmpeg, Playwright deps, curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    wget \
    gnupg \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python deps
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Force-create dummy package records for the old fonts so Playwright's installer skips them
RUN mkdir -p /tmp/fake-ttf/DEBIAN \
    && printf "Package: ttf-unifont\nVersion: 1.0\nArchitecture: all\nDescription: dummy\n" > /tmp/fake-ttf/DEBIAN/control \
    && dpkg-deb --build /tmp/fake-ttf /tmp/ttf-unifont.deb \
    && dpkg -i /tmp/ttf-unifont.deb \
    && printf "Package: ttf-ubuntu-font-family\nVersion: 1.0\nArchitecture: all\nDescription: dummy\n" > /tmp/fake-ttf/DEBIAN/control \
    && dpkg-deb --build /tmp/fake-ttf /tmp/ttf-ubuntu-font-family.deb \
    && dpkg -i /tmp/ttf-ubuntu-font-family.deb

# Install Playwright browsers and system dependencies
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy application code
COPY . .

# Ensure temp directory exists
RUN mkdir -p /app/temp/downloads

EXPOSE 8000

# Run FastAPI with uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
