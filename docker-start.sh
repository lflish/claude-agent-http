#!/bin/bash
# ============================================
# Claude Agent HTTP - Docker Startup Script
# ============================================
# This script validates configuration and starts Docker containers
# with proper error checking and helpful messages.
#
# Usage:
#   ./docker-start.sh [OPTIONS]
#
# Options:
#   --postgres        Enable PostgreSQL mode
#   --bind-mounts     Use bind mounts (requires setup)
#   --build           Rebuild images before starting
#   --stop            Stop running containers
#   --down            Stop and remove containers
#   -h, --help        Show this help message
#
# ============================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Default options
USE_POSTGRES=false
USE_BIND_MOUNTS=false
BUILD_IMAGES=false
STOP_CONTAINERS=false
DOWN_CONTAINERS=false

# ============================================
# Helper Functions
# ============================================

print_header() {
    echo -e "${BLUE}============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

show_help() {
    cat << EOF
Claude Agent HTTP - Docker Startup Script

Usage:
  ./docker-start.sh [OPTIONS]

Options:
  --postgres        Enable PostgreSQL mode (enterprise deployment)
  --bind-mounts     Use bind mounts instead of named volumes
  --build           Rebuild Docker images before starting
  --stop            Stop running containers
  --down            Stop and remove containers (including volumes)
  -h, --help        Show this help message

Examples:
  # Start with SQLite + named volumes (default)
  ./docker-start.sh

  # Start with PostgreSQL
  ./docker-start.sh --postgres

  # Start with bind mounts (development mode)
  ./docker-start.sh --bind-mounts

  # Rebuild and start
  ./docker-start.sh --build

  # Stop containers
  ./docker-start.sh --stop

Configuration:
  Edit .env file to customize settings
  Required: ANTHROPIC_API_KEY

For detailed documentation, see DOCKER.md
EOF
}

# ============================================
# Parse Arguments
# ============================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --postgres)
            USE_POSTGRES=true
            shift
            ;;
        --bind-mounts)
            USE_BIND_MOUNTS=true
            shift
            ;;
        --build)
            BUILD_IMAGES=true
            shift
            ;;
        --stop)
            STOP_CONTAINERS=true
            shift
            ;;
        --down)
            DOWN_CONTAINERS=true
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# ============================================
# Handle Stop/Down Commands
# ============================================

if [ "$STOP_CONTAINERS" = true ]; then
    print_header "Stopping Containers"
    docker-compose stop
    print_success "Containers stopped"
    exit 0
fi

if [ "$DOWN_CONTAINERS" = true ]; then
    print_header "Stopping and Removing Containers"
    docker-compose down
    print_success "Containers stopped and removed"
    print_info "To remove volumes too, run: docker-compose down -v"
    exit 0
fi

# ============================================
# Configuration Validation
# ============================================

print_header "Configuration Validation"

# Check if .env file exists
if [ ! -f .env ]; then
    print_error ".env file not found"
    print_info "Creating .env from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        print_success ".env file created"
        print_warning "Please edit .env and set your ANTHROPIC_API_KEY"
        exit 1
    else
        print_error ".env.example not found"
        exit 1
    fi
fi

print_success ".env file found"

# Load environment variables
set -a
source .env
set +a

# Validate ANTHROPIC_API_KEY
if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "your_api_key_here" ]; then
    print_error "ANTHROPIC_API_KEY is not set or invalid"
    print_info "Please edit .env and set your Anthropic API key"
    print_info "Get your API key from: https://console.anthropic.com/"
    exit 1
fi

print_success "ANTHROPIC_API_KEY is set"

# Validate storage configuration
STORAGE_TYPE="${CLAUDE_AGENT_SESSION_STORAGE:-sqlite}"
if [ "$STORAGE_TYPE" = "postgresql" ]; then
    if [ "$USE_POSTGRES" = false ]; then
        print_warning "CLAUDE_AGENT_SESSION_STORAGE=postgresql but --postgres flag not set"
        print_info "Enabling PostgreSQL mode automatically..."
        USE_POSTGRES=true
    fi
    print_success "Storage: PostgreSQL (enterprise mode)"
else
    if [ "$USE_POSTGRES" = true ]; then
        print_warning "--postgres flag set but CLAUDE_AGENT_SESSION_STORAGE=$STORAGE_TYPE"
        print_info "You may want to set CLAUDE_AGENT_SESSION_STORAGE=postgresql in .env"
    fi
    print_success "Storage: $STORAGE_TYPE"
fi

# ============================================
# Bind Mounts Setup
# ============================================

if [ "$USE_BIND_MOUNTS" = true ]; then
    print_header "Bind Mounts Configuration"

    # Check if override file exists
    if [ ! -f docker-compose.override.yml ]; then
        print_info "Creating docker-compose.override.yml from template..."
        if [ -f docker-compose.override.bindmounts.yml ]; then
            cp docker-compose.override.bindmounts.yml docker-compose.override.yml
            print_success "docker-compose.override.yml created"
        else
            print_error "docker-compose.override.bindmounts.yml not found"
            exit 1
        fi
    else
        print_success "docker-compose.override.yml exists"
    fi

    # Check host directories
    HOST_USER_DATA="${HOST_USER_DATA_DIR:-/opt/claude-code-http/claude-users}"
    HOST_DB="${HOST_DB_DIR:-/opt/claude-code-http/db}"

    print_info "Checking host directories..."

    for dir in "$HOST_USER_DATA" "$HOST_DB"; do
        if [ ! -d "$dir" ]; then
            print_warning "Directory does not exist: $dir"
            print_info "Creating directory with sudo..."
            sudo mkdir -p "$dir"
            sudo chown -R "$(id -u):$(id -g)" "$dir"
            print_success "Created and configured: $dir"
        elif [ ! -w "$dir" ]; then
            print_warning "Directory not writable: $dir"
            print_info "Fixing permissions with sudo..."
            sudo chown -R "$(id -u):$(id -g)" "$dir"
            print_success "Fixed permissions: $dir"
        else
            print_success "Directory OK: $dir"
        fi
    done

    # Set UID/GID if not already set
    if [ -z "$UID" ] || [ -z "$GID" ]; then
        print_info "Setting UID/GID to match current user"
        export UID=$(id -u)
        export GID=$(id -g)
        print_success "UID=$UID, GID=$GID"
    fi
else
    print_info "Using named volumes (Docker-managed)"
    # Clean up override file if exists
    if [ -f docker-compose.override.yml ]; then
        print_warning "Found docker-compose.override.yml (not using it)"
        print_info "To use bind mounts, run with --bind-mounts flag"
    fi
fi

# ============================================
# Build Docker Images
# ============================================

if [ "$BUILD_IMAGES" = true ]; then
    print_header "Building Docker Images"
    docker-compose build --no-cache
    print_success "Images built successfully"
fi

# ============================================
# Start Containers
# ============================================

print_header "Starting Containers"

# Build docker-compose command
COMPOSE_CMD="docker-compose"

if [ "$USE_POSTGRES" = true ]; then
    COMPOSE_CMD="$COMPOSE_CMD --profile postgres"
    print_info "PostgreSQL mode enabled"
fi

COMPOSE_CMD="$COMPOSE_CMD up -d"

print_info "Running: $COMPOSE_CMD"
eval $COMPOSE_CMD

print_success "Containers started successfully"

# ============================================
# Health Check
# ============================================

print_header "Health Check"

print_info "Waiting for services to be ready..."
sleep 5

# Check if app container is running
if docker ps | grep -q claude-agent-http; then
    print_success "claude-agent-http container is running"

    # Test health endpoint
    MAX_RETRIES=10
    RETRY_COUNT=0

    while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
        if curl -sf http://localhost:${API_PORT:-8000}/health > /dev/null 2>&1; then
            print_success "Health check passed"
            break
        else
            RETRY_COUNT=$((RETRY_COUNT + 1))
            if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
                print_warning "Health check failed after $MAX_RETRIES retries"
                print_info "Check logs: docker-compose logs -f app"
            else
                sleep 2
            fi
        fi
    done
else
    print_error "claude-agent-http container is not running"
    print_info "Check logs: docker-compose logs app"
    exit 1
fi

# Check PostgreSQL if enabled
if [ "$USE_POSTGRES" = true ]; then
    if docker ps | grep -q claude-agent-postgres; then
        print_success "PostgreSQL container is running"
    else
        print_warning "PostgreSQL container is not running"
    fi
fi

# ============================================
# Summary
# ============================================

print_header "Deployment Summary"

echo -e "Status:        ${GREEN}Running${NC}"
echo -e "Storage:       ${STORAGE_TYPE}"
echo -e "Volumes:       $([ "$USE_BIND_MOUNTS" = true ] && echo "Bind mounts" || echo "Named volumes")"
echo -e "API Endpoint:  ${BLUE}http://localhost:${API_PORT:-8000}${NC}"
echo -e "Health Check:  ${BLUE}http://localhost:${API_PORT:-8000}/health${NC}"

if [ "$USE_POSTGRES" = true ]; then
    echo -e "PostgreSQL:    ${BLUE}localhost:${POSTGRES_PORT:-5432}${NC}"
fi

echo ""
print_info "Useful commands:"
echo "  View logs:    docker-compose logs -f"
echo "  Stop:         ./docker-start.sh --stop"
echo "  Stop & clean: ./docker-start.sh --down"
echo "  Rebuild:      ./docker-start.sh --build"

echo ""
print_success "Deployment complete!"
