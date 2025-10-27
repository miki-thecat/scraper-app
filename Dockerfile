# ========================================
# Multi-stage Dockerfile for Production
# ========================================

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ========================================
# Stage 2: Runtime
FROM python:3.11-slim

LABEL maintainer="your-email@example.com"
LABEL description="Scraper App - AI-powered News Risk Analysis"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser

WORKDIR /app

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser cli ./cli
COPY --chown=appuser:appuser ml ./ml
COPY --chown=appuser:appuser templates ./templates
COPY --chown=appuser:appuser statics ./statics
COPY --chown=appuser:appuser migrations ./migrations
COPY --chown=appuser:appuser run.py .
COPY --chown=appuser:appuser config.py .

# Create instance directory for SQLite (if used)
RUN mkdir -p /app/instance && chown -R appuser:appuser /app/instance

# Switch to non-root user
USER appuser

# Add local Python packages to PATH
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.main

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Default command: run with gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "app.main:app"]
