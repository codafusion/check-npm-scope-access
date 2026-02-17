# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## [Unreleased]

## [1.0.0] - 2026-02-17

### Added
- Initial public release.
- Initial release workflow for tagged releases (`vX.Y.Z`) with automatic moving major tag updates (for example `v1`).
- Unit tests for scope parsing, package discovery, HTTP handling, and main execution paths.
- CI test execution (`pytest`) and syntax check (`py_compile`).
- Security policy (`SECURITY.md`).

### Changed
- No `package.json` files now result in a successful notice instead of a failure.
- Error reporting now includes categorized HTTP/network failure context.

### Documentation
- README: added CI badge and release section.
- CONTRIBUTING: clarified local checks and pull request rules.
