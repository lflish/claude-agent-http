#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Claude Agent HTTP...${NC}"

# Check if running as root
if [ "$(id -u)" = "0" ]; then
    echo -e "${YELLOW}Warning: Running as root user. This is not recommended for security.${NC}"
fi

# Directories that need to be writable
REQUIRED_DIRS=(
    "/data/claude-users"
    "/data/db"
)

# Function to check and create directories
ensure_directories() {
    for dir in "${REQUIRED_DIRS[@]}"; do
        if [ ! -d "$dir" ]; then
            echo -e "${YELLOW}Creating directory: $dir${NC}"
            mkdir -p "$dir" 2>/dev/null || {
                echo -e "${RED}Error: Cannot create directory $dir${NC}"
                echo -e "${YELLOW}Please ensure the volume is mounted with proper permissions.${NC}"
                return 1
            }
        fi

        # Test write permission
        if [ -w "$dir" ]; then
            echo -e "${GREEN}✓ Directory $dir is writable${NC}"
        else
            echo -e "${RED}✗ Directory $dir is NOT writable${NC}"
            echo -e "${YELLOW}Current user: $(id)${NC}"
            echo -e "${YELLOW}Directory permissions: $(ls -ld $dir)${NC}"
            echo -e "${YELLOW}Please fix permissions on the host:${NC}"
            echo -e "${YELLOW}  sudo chown -R $(id -u):$(id -g) /opt/claude-code-http/${NC}"
            return 1
        fi
    done
    return 0
}

# Ensure all required directories exist and are writable
if ! ensure_directories; then
    echo -e "${RED}Failed to setup required directories. Exiting.${NC}"
    exit 1
fi

echo -e "${GREEN}All directory checks passed. Starting application...${NC}"
echo ""

# Execute the main application
exec python -m claude_agent_http.main "$@"
