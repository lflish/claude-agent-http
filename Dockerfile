# Dockerfile for Claude Agent HTTP
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY claude_agent_http/ ./claude_agent_http/
COPY config.yaml .

# Create data directories
RUN mkdir -p /data/users

# Expose port
EXPOSE 8000

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV CLAUDE_AGENT_USER_BASE_DIR=/data/users
ENV CLAUDE_AGENT_SESSION_STORAGE=sqlite

# Start command
CMD ["uvicorn", "claude_agent_http.main:app", "--host", "0.0.0.0", "--port", "8000"]
