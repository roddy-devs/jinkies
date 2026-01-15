# Changelog

All notable changes to this project will be documented in this file.

## [3.0.0] - 2024-01-15

### Changed
- **BREAKING**: Raspberry Pi only - removed all non-Pi documentation and setup
- Simplified to single setup script: `setup-pi.sh`
- Streamlined README to focus only on Raspberry Pi deployment
- Removed Docker, generic Linux, and Mac setup instructions
- One-command setup with guided configuration

### Added
- `setup-pi.sh` - Comprehensive one-command setup script
- Automatic systemd service configuration
- Interactive configuration validation
- Choice of foreground or service mode startup

### Removed
- QUICKSTART.md (replaced with simplified README)
- IMPLEMENTATION.md (technical details not needed for Pi users)
- CONTRIBUTING.md (simplified project)
- Dockerfile and docker-compose.yml (Pi-specific deployment only)
- Generic setup.py (replaced with setup-pi.sh)

## [2.0.0] - 2024-01-15

### Added
- Django webhook integration
- Raspberry Pi support
- SSH tunnel support
- No AWS required - CloudWatch optional

### Changed
- Replaced Flask with Django
- Made CloudWatch integration optional

### Removed
- Flask dependency
- AWS Lambda example

## [1.0.1] - 2024-01-15

### Security
- Updated aiohttp from 3.9.1 to 3.13.3 to address multiple security vulnerabilities

## [1.0.0] - 2024-01-15

### Added
- Initial release
- Discord bot with slash commands
- Alert management
- GitHub integration
- CloudWatch logs integration
