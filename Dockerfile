# Multi-stage build for optimized image
FROM python:3.11-slim as builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    bash \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Create non-root user
RUN useradd -m -s /bin/bash music && \
    mkdir -p /app/data/chroma /app/logs && \
    chown -R music:music /app

# Copy application code
COPY src/ ./src/
COPY docker-entrypoint.sh .

# Set permissions
RUN chmod +x docker-entrypoint.sh && \
    chown -R music:music /app

# Switch to non-root user
USER music

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health', timeout=5)" || exit 1

# Default command
CMD ["./docker-entrypoint.sh"]