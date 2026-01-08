# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive troubleshooting section in Docker documentation (DOCKER.md and DOCKER_CN.md)
  - 6 common issues with detailed root causes and solutions
  - Permission denied errors with outdated Docker images
  - Health check 503 errors (HOME variable, API key, user mismatch)
  - Port conflicts resolution
  - Bind mount permission errors
  - PostgreSQL connection failures
  - Container restart loops diagnostics
- Debugging commands section for logs, containers, and shell access
- Complete clean and rebuild procedures
- Help resources and issue reporting guidelines
- Troubleshooting references in README.md and README_CN.md
- Support for custom API endpoints and model configuration
- Bilingual documentation (English and Chinese)
- gosu tool for secure user switching in Docker containers

### Changed
- Unified Docker configuration with single docker-compose.yml file
- Separated PostgreSQL configuration into dedicated docker-compose.postgres.yml
- Updated documentation structure for better clarity
- Improved CLAUDE.md with enhanced guidance
- Docker entrypoint now automatically fixes volume permissions before switching to non-root user
- Container starts as root, fixes permissions, then switches to claudeuser for security

### Fixed
- **Critical: Docker volume permission issues with named volumes**
  - Fixed root:root ownership on Docker named volumes preventing writes
  - Automatic permission fixing in entrypoint script before application starts
  - Database file creation now works seamlessly with named volumes
  - No manual intervention required for permission management
- HOME environment variable not passed through in docker-compose.yml
- Docker compose syntax error with PostgreSQL depends_on configuration
- Permission issues when creating sessions in Docker containers
- Outdated Docker image caching causing permission denied errors
- PostgreSQL dependency issue in docker-compose.yml

### Security
- Implemented non-root user execution in Docker containers
- Enhanced path validation and user directory isolation
- Secure user switching with gosu (starts as root, switches to claudeuser)

## [1.0.0] - 2026-01-06

### Added
- Initial release with multi-user session management
- HTTP REST API wrapper for Claude Agent SDK
- Session storage backends: Memory, SQLite, PostgreSQL
- Streaming response support via Server-Sent Events (SSE)
- User directory isolation and security
- Configurable via YAML with environment variable overrides
- Docker deployment support
- API documentation and Postman collection

[Unreleased]: https://github.com/lflish/claude-agent-http/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/lflish/claude-agent-http/releases/tag/v1.0.0
