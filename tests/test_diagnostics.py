"""Tests for diagnostics."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smartbulb_mgmt.const import (
    CONF_BULB_ENTITIES,
    CONF_HOLIDAY_ENTITY,
    CONF_SWITCH_ENTITY,
    DOMAIN,
)
from custom_components.smartbulb_mgmt.diagnostics import (
    async_get_config_entry_diagnostics,
)
from homeassistant.core import HomeAssistant


async def test_diagnostics(hass: HomeAssistant) -> None:
    """Diagnostics show the settings and the current states."""
    hass.states.async_set("switch.porch_switch", "on")
    hass.states.async_set("light.porch_bulb", "on", {"brightness": 128})
    hass.states.async_set("sensor.holiday_lighting_status", "On")
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_SWITCH_ENTITY: "switch.porch_switch",
            CONF_BULB_ENTITIES: ["light.porch_bulb", "light.old_bulb"],
            CONF_HOLIDAY_ENTITY: "sensor.holiday_lighting_status",
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    diag = await async_get_config_entry_diagnostics(hass, entry)

    assert diag["data"][CONF_SWITCH_ENTITY] == "switch.porch_switch"
    assert diag["switch"] == {"entity_id": "switch.porch_switch", "state": "on"}
    assert diag["bulbs"][0]["brightness"] == 128
    assert diag["bulbs"][1] == {"entity_id": "light.old_bulb", "state": None}
    assert diag["holiday_running"] is True
    assert diag["holiday_control"] is None
    assert diag["missing_entities"] == ["light.old_bulb"]
