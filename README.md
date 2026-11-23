# Smart Bulb Management

A UI-configurable Home Assistant integration for smart light switches and dimmers running in **Smart Bulb Mode** (domain: `smartbulb_mgmt`), designed to work cleanly alongside **Holiday Lighting** (`sensor.holiday_lighting_status`) and other lighting automations.

## Features

- **Zero-Bounce Two-Way Sync:** Tracks its own Home Assistant `Context` IDs when passively updating the switch state from bulb changes, so other lighting integrations never see a false manual override.
- **Holiday Lighting Awareness:** Watches `sensor.holiday_lighting_status` (`On` vs. `Done for tonight`). When holiday lighting is `On`, `smartbulb_mgmt` avoids overwriting colors or brightness unless you enable **Override holiday lighting**.
- **Configurable Manual-Off Behavior:** Choose whether turning the switch Off while holiday lighting is running only turns off the bulbs, or also turns off a linked holiday-lighting `switch` / `input_boolean`.
- **Default Color & Brightness:** Configure a default **RGB color**, **Color Temperature (Kelvin)**, and **Brightness %** for when the switch turns On while holiday lighting is not `On` (or when override is enabled).
- **UI Setup:** Configure everything from **Settings → Devices & Services → Add Integration**.

## Installation

### Marketplace (Home Assistant 2026.11 and newer)

1. Go to **Settings → Marketplace**, choose **Add from link**, enter `bisman-automations/ha-smartbulb-mgmt` under **GitHub link**, and select **Add**.
2. Install **Smart Bulb Management**.
3. If a repair asks you to restart Home Assistant, restart it.

### HACS (Home Assistant 2026.10 and older)

1. In **HACS**, open the menu (⋮), choose **Custom repositories**, and add `bisman-automations/ha-smartbulb-mgmt` as an **Integration**.
2. Download **Smart Bulb Management** and restart Home Assistant.

## Configuration

Go to **Settings → Devices & Services → Add Integration** and search for **Smart Bulb Management**.

## Diagnostics and Debug Logs

Enable debug logging for `custom_components.smartbulb_mgmt` in Home Assistant before opening an issue, and check any logs before sharing.
