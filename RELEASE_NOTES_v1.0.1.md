# Release v1.0.1

**Critical bug fix release with comprehensive documentation improvements.**

## 🔥 Critical Fixes

### Docker Volume Permission Issues
- **Fixed root:root ownership on Docker named volumes preventing writes**
  - Automatic permission fixing in entrypoint script before application starts
  - Database file creation now works seamlessly with named volumes
  - No manual intervention required for permission management
- Container starts as root, fixes permissions, then switches to claudeuser for security

## 🐛 Bug Fixes

- HOME environment variable not passed through in docker-compose.yml
- Docker compose syntax error with PostgreSQL depends_on configuration
- Permission issues when creating sessions in Docker containers
- Outdated Docker image caching causing permission denied errors
- PostgreSQL dependency issue in docker-compose.yml

## 📚 Documentation

### Comprehensive Troubleshooting Section
Added detailed troubleshooting guides covering 6 common issues:
1. Permission denied errors with outdated Docker images
2. Health check 503 errors (HOME variable, API key, user mismatch)
3. Port conflicts resolution
4. Bind mount permission errors
5. PostgreSQL connection failures
6. Container restart loops diagnostics

### Additional Documentation
- Debugging commands section for logs, containers, and shell access
- Complete clean and rebuild procedures
- Help resources and issue reporting guidelines
- Troubleshooting references in README.md and README_CN.md
- Bilingual documentation (English and Chinese)

## ✨ Enhancements

### Docker Configuration
- Unified Docker configuration with single docker-compose.yml file
- Separated PostgreSQL configuration into dedicated docker-compose.postgres.yml
- Updated documentation structure for better clarity
- Improved CLAUDE.md with enhanced guidance

### New Features
- Support for custom API endpoints and model configuration
- gosu tool for secure user switching in Docker containers
- Docker entrypoint now automatically fixes volume permissions before switching to non-root user

## 🔒 Security

- Implemented non-root user execution in Docker containers
- Enhanced path validation and user directory isolation
- Secure user switching with gosu (starts as root, switches to claudeuser)

## 📦 Installation

### Docker (Recommended)

```bash
# Pull the latest release
git clone https://github.com/lflish/claude-agent-http.git
cd claude-agent-http
git checkout v1.0.1

# Setup and run
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

### Manual Installation

```bash
# Clone and checkout
git clone https://github.com/lflish/claude-agent-http.git
cd claude-agent-http
git checkout v1.0.1

# Install and run
pip install -r requirements.txt
export ANTHROPIC_API_KEY="your_api_key"
python -m claude_agent_http.main
```

## 🔗 Documentation

- [Docker Deployment Guide](DOCKER.md) ([中文版](DOCKER_CN.md))
- [API Examples](docs/API_EXAMPLES.md)
- [Configuration Guide](CLAUDE.md)
- [Changelog](CHANGELOG.md)

## 🙏 Acknowledgments

This release includes contributions and bug reports from the community. Thank you for helping improve Claude Agent HTTP!

## 📝 Full Changelog

**Full Changelog**: https://github.com/lflish/claude-agent-http/compare/v1.0.0...v1.0.1

---

**Note**: This is a critical bug fix release. All users running v1.0.0 are encouraged to upgrade to v1.0.1 to resolve Docker volume permission issues.
