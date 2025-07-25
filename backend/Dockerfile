# Dockerfile for Legal AI Backend - Production Optimized
FROM python:3.13-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libmagic1 \
    libmagic-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install build tools
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install base requirements with retry logic
RUN pip install --no-cache-dir -r requirements.txt || \
    (sleep 5 && pip install --no-cache-dir -r requirements.txt) || \
    (sleep 10 && pip install --no-cache-dir -r requirements.txt)

# Copy ML requirements but don't install by default
COPY requirements-ml.txt* ./

# Production image
FROM python:3.13-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    libpq5 \
    libmagic1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r legalai && useradd -r -g legalai legalai

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=legalai:legalai . .

# Create necessary directories
RUN mkdir -p /app/uploads /app/logs /app/temp && \
    chown -R legalai:legalai /app

# Security: Remove unnecessary files
RUN find . -name "*.pyc" -delete && \
    find . -name "__pycache__" -type d -exec rm -rf {} + || true && \
    rm -rf .git .env* tests/ scripts/

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Switch to non-root user
USER legalai

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV ENVIRONMENT=production

# Run with gunicorn for production
CMD ["gunicorn", "main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "50"]