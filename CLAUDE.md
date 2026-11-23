# Smart Bulb Management (`ha-smartbulb-mgmt`)

Home Assistant custom integration (`custom_components/smartbulb_mgmt`, domain `smartbulb_mgmt`), installed through Marketplace or HACS.

## Shared rules (every bisman-automations repo)

- The version lives in `custom_components/smartbulb_mgmt/manifest.json` and must match `CHANGELOG.md` and the `vX.Y.Z` tag.
- Never include `categories` in `manifest.json` or `Pillow` in `requirements` (rejected by `hassfest`).
- Minimum Home Assistant is `2026.3.0` (Python `3.14`).
- Never bounce passive two-way switch updates back to bulbs; always tag internal switch calls with a tracked `Context`.
