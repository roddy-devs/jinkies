# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2024-01-15

### Security
- Updated aiohttp from 3.9.1 to 3.13.3 to address multiple security vulnerabilities:
  - CVE: HTTP Parser auto_decompress zip bomb vulnerability
  - CVE: Denial of Service when parsing malformed POST requests
  - CVE: Directory traversal vulnerability

## [1.0.0] - 2024-01-15

### Added
- Initial release of Jinkies Discord bot
- Discord slash commands for log management:
  - `/logs` - Retrieve application logs with filtering
  - `/logs-tail` - Stream logs in real-time
  - `/logs-stop` - Stop log streaming
- Alert management commands:
  - `/alerts` - List recent alerts
  - `/alert <id>` - View specific alert details
  - `/ack <id>` - Acknowledge an alert
- GitHub integration commands:
  - `/create-pr <id>` - Create PR from alert
  - `/create-issue <id>` - Create issue from alert
- AWS CloudWatch Logs integration
  - Log querying and filtering
  - Support for multiple log groups
  - Time-based and level-based filtering
- Alert system with SQLite persistence
  - Alert storage and retrieval
  - Acknowledgement tracking
  - GitHub PR/issue linking
- Rich Discord embeds for alerts
  - Severity indicators
  - Stack traces
  - Related logs
  - Environment context
- Webhook endpoint for receiving alerts
  - Support for custom alert payloads
  - AWS SNS integration
- Security features:
  - Role-based access control
  - Message length protection
  - Rate limiting
  - Environment separation
- Documentation:
  - Comprehensive README
  - Quick start guide
  - Contributing guidelines
  - Django integration example
  - AWS Lambda forwarder example
- Testing:
  - Unit tests for core functionality
  - GitHub Actions CI/CD
- Docker support:
  - Dockerfile for containerization
  - Docker Compose for multi-service deployment

### Security
- Implemented role-based command permissions
- Added environment variable validation
- Secure credential management through .env
- IAM policy examples for least-privilege access

## [Unreleased]

### Planned
- AI-generated fix suggestions from logs
- Auto-close alerts on PR merge
- Log snapshots attached to PRs
- Web dashboard mirroring Discord state
- Metrics and analytics
- Custom alert rules and thresholds
