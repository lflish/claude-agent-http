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

# Create data directories
RUN mkdir -p /data/claude-users /data/db

# Expose API port
EXPOSE 8000

# Health check using Python
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

# Run the application
CMD ["python", "-m", "claude_agent_http.main"]
