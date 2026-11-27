"""Diagnostics for Smart Bulb Management."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from . import SmartBulbConfigEntry


def _state(hass: HomeAssistant, entity_id: str | None) -> dict[str, Any] | None:
    if not entity_id:
        return None
    state = hass.states.get(entity_id)
    if state is None:
        return {"entity_id": entity_id, "state": None}
    info: dict[str, Any] = {"entity_id": entity_id, "state": state.state}
    for attr in ("brightness", "color_mode", "supported_color_modes"):
        if attr in state.attributes:
            info[attr] = state.attributes[attr]
    return info


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: SmartBulbConfigEntry
) -> dict[str, Any]:
    """Return the settings and the current switch, bulb and holiday states."""
    sync = entry.runtime_data
    return {
        "data": dict(entry.data),
        "options": dict(entry.options),
        "switch": _state(hass, sync.switch_entity),
        "bulbs": [_state(hass, entity_id) for entity_id in sync.bulb_entities],
        "holiday": _state(hass, sync.holiday_entity),
        "holiday_control": _state(hass, sync.holiday_control_entity),
        "holiday_running": sync.is_holiday_running(),
        "missing_entities": sorted(sync.missing),
    }
