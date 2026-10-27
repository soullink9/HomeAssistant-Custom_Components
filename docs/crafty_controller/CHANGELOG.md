# Changelog

All notable changes to this project are documented here. The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project follows [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-10-18

Initial release.

### Added
- One Home Assistant device per Crafty server.
- Switch to start and stop a server.
- Status sensor showing whether the server is online (answering) or offline.
- Server name (device name) and port (`port` attribute) on each entity.
- Config flow asking for the Crafty URL, API token and SSL verification.
- Servers added in Crafty later appear without reloading the integration.
- Per-server error isolation: one unreadable server does not affect the others.
- Request timeouts and clear errors when Crafty is unreachable or replies unexpectedly.
- Brand icons, a simulation test, and hassfest/HACS validation workflow.
