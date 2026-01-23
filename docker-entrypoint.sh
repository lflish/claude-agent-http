#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Starting Claude Agent HTTP...${NC}"

# Directories that need to be writable
REQUIRED_DIRS=(
    "/home/claudeuser/.claude"
    "/data/claude-users"
)

# If running as root, fix permissions and switch to claudeuser
if [ "$(id -u)" = "0" ]; then
    echo -e "${GREEN}Running as root, fixing volume permissions...${NC}"

    # Ensure directories exist and have correct permissions
    for dir in "${REQUIRED_DIRS[@]}"; do
        if [ ! -d "$dir" ]; then
            echo -e "${YELLOW}Creating directory: $dir${NC}"
            mkdir -p "$dir"
        fi

        # Fix ownership
        chown -R claudeuser:claudeuser "$dir"
        echo -e "${GREEN}✓ Fixed permissions for $dir${NC}"
    done

    # Fix home directory permissions
    chown -R claudeuser:claudeuser /home/claudeuser

    echo -e "${GREEN}Switching to claudeuser...${NC}"
    # Switch to claudeuser and execute the application
    exec gosu claudeuser python -m claude_agent_http.main "$@"
else
    # Not running as root - check if directories are writable
    echo -e "${YELLOW}Warning: Not running as root (current user: $(id))${NC}"

    # Function to check directories
    ensure_directories() {
        for dir in "${REQUIRED_DIRS[@]}"; do
            if [ ! -d "$dir" ]; then
                echo -e "${RED}Error: Directory $dir does not exist${NC}"
                return 1
            fi

            # Test write permission
            if [ -w "$dir" ]; then
                echo -e "${GREEN}✓ Directory $dir is writable${NC}"
            else
                echo -e "${RED}✗ Directory $dir is NOT writable${NC}"
                echo -e "${YELLOW}Current user: $(id)${NC}"
                echo -e "${YELLOW}Directory permissions: $(ls -ld $dir)${NC}"
                return 1
            fi
        done
        return 0
    }

    # Ensure all required directories are writable
    if ! ensure_directories; then
        echo -e "${RED}Failed to setup required directories. Exiting.${NC}"
        exit 1
    fi

    echo -e "${GREEN}All directory checks passed. Starting application...${NC}"
    echo ""

    # Execute the main application
    exec python -m claude_agent_http.main "$@"
fi
