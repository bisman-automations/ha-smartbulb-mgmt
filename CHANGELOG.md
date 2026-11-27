# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-11-27

### Added

- First release of Smart Bulb Management: link a switch or dimmer in Smart Bulb Mode to the smart bulbs it powers, set up from **Settings > Devices & services**.
- Two-way sync: the switch drives the bulbs, and bulbs changed elsewhere move the switch without anything bouncing back, even for bulbs that report slowly (Zigbee groups, cloud bulbs).
- Holiday Lighting awareness: while the holiday status is **On**, the switch leaves holiday colors alone unless you turn on **Override holiday lighting**, and it can pause Holiday Lighting when you turn the switch off.
- Default RGB color, color temperature and brightness for when the switch turns the bulbs on.
- **Reconfigure** to choose a different switch or dimmer for the same bulbs.
- Repairs when the switch or a bulb is deleted or renamed.
- Diagnostics download.
- A switch that drops off the network and comes back isn't treated as a press, and light commands that fail are logged as warnings.

[0.1.0]: https://github.com/bisman-automations/ha-smartbulb-mgmt/releases/tag/v0.1.0
