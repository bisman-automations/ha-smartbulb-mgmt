# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-11-22

### Added
- Initial release of Smart Bulb Management (`smartbulb_mgmt`).
- UI Config Flow and Options Flow for linking a smart switch/dimmer in Smart Bulb Mode to target smart bulbs.
- Zero-bounce two-way sync using Home Assistant `Context` ID tracking so passive switch updates do not trigger false manual overrides in `ha-holiday-lighting`.
- Holiday lighting awareness via `sensor.holiday_lighting_status` (`On` vs. `Done for tonight`) with optional override and optional pause-on-manual-off.
- Configurable default RGB color, Color Temperature (Kelvin), and Brightness % when holiday lighting is not running.
