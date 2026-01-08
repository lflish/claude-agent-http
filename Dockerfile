# Multi-stage build for Claude Agent HTTP

FROM python:3.12-slim AS base

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies using Tsinghua PyPI mirror for better connectivity
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# Copy application code
COPY . .

# Copy and set up entrypoint script
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Create non-root user and group
# Note: User ID can be overridden via docker-compose user: parameter
RUN groupadd -r claudeuser && \
    useradd -r -g claudeuser -u 1000 -m -s /bin/bash claudeuser

# Set HOME environment variable for claudeuser
ENV HOME=/home/claudeuser

# Create data directories with proper permissions
# These will be used if volumes are not mounted
RUN mkdir -p /data/claude-users /data/db && \
    chown -R claudeuser:claudeuser /data /app /home/claudeuser

# Note: Do not switch to non-root user here
# The user will be specified in docker-compose via the 'user' parameter
# This allows flexibility to match host user UID/GID

# Expose API port
EXPOSE 8000

# Health check using Python
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Use entrypoint script to handle permissions and startup
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Default command (can be overridden)
CMD []
