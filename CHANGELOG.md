# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.3] - 2026-02-12

### Fixed
- **Critical: OOM (Out of Memory) killing claude processes**
  - Root cause: `deploy.resources.limits` in docker-compose.yml is ignored without Docker Swarm mode, resulting in no container memory limits
  - A single claude CLI subprocess reached 71.5GB virtual memory, triggering host-level OOM killer
  - Replaced with `mem_limit: 8g` / `memswap_limit: 10g` which works with standard `docker-compose up`

### Added
- **Multi-layer memory protection system**:
  - Docker layer: `mem_limit` hard cap (8GB) prevents host OOM
  - Application layer: `memory_limit_mb` soft limit, refuses new sessions when exceeded
  - Idle eviction: `idle_session_timeout` auto-releases in-memory clients after inactivity (default 600s)
  - LRU pressure recovery: periodic cleanup evicts oldest sessions first when memory is high
  - `oom_score_adj: -100` reduces OOM killer targeting probability
- Process tree memory monitoring in health endpoint (includes child process RSS)
- New config options: `memory_limit_mb`, `idle_session_timeout` with env var overrides
- Memory protection documentation in README.md and README_CN.md

### Changed
- Periodic cleanup interval reduced from 120s to 60s for faster response to memory pressure
- Default `max_turns` set to 50 (was 200) to bound per-session memory growth
- Default `max_sessions` tuned to 20 with `max_concurrent_requests: 5`

## [Unreleased]

### Fixed
- **Critical: SQLite storage performance issues causing high CPU and I/O usage**
  - Implemented persistent database connection (eliminated reconnection overhead)
  - Enabled WAL (Write-Ahead Logging) mode for better concurrency
  - Reduced synchronous level to NORMAL (still safe, significantly faster)
  - Increased cache size from 8MB to 40MB
  - Configured memory-based temporary storage
  - Added proper connection locking for thread-safety
  - Performance improvement: 10-100x faster (Touch operations: 6,385 ops/sec)
  - Touch operations are critical as they occur on every message

### Added
- Comprehensive performance optimization documentation (SQLITE_OPTIMIZATION.md)
  - Detailed explanation of performance issues and solutions
  - Performance benchmarks and testing methodology
  - Troubleshooting guide for SQLite-related issues
  - Migration and monitoring recommendations
- Performance test script (test_sqlite_perf.py) for validation

## [1.0.1] - 2026-01-08

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

[Unreleased]: https://github.com/lflish/claude-agent-http/compare/v1.0.3...HEAD
[1.0.3]: https://github.com/lflish/claude-agent-http/compare/v1.0.1...v1.0.3
[1.0.1]: https://github.com/lflish/claude-agent-http/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/lflish/claude-agent-http/releases/tag/v1.0.0
