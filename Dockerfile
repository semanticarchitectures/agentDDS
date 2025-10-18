# Multi-stage Dockerfile for MCP-DDS Gateway
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    openssl \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# ============================================
# Stage: Dependencies
# ============================================
FROM base as dependencies

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# Stage: Runtime
# ============================================
FROM base as runtime

# Copy Python dependencies from dependencies stage
COPY --from=dependencies /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin

# Copy application code
COPY mcp_gateway.py .
COPY agent_client.py .
COPY config_manager.py .
COPY dds_manager.py .
COPY rate_limiter.py .
COPY metrics_collector.py .
COPY health_server.py .

# Copy configuration files
COPY config/ config/

# Copy scripts
COPY scripts/ scripts/
RUN chmod +x scripts/*.sh

# Create directories for certificates and logs
RUN mkdir -p certs logs

# Expose ports
EXPOSE 8080
EXPOSE 9090

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:9090/health || exit 1

# Run as non-root user
RUN useradd -m -u 1000 gateway && \
    chown -R gateway:gateway /app
USER gateway

# Default command
CMD ["python", "mcp_gateway.py"]
