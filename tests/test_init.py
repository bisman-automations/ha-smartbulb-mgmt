"""Tests for Smart Bulb Management state sync and holiday lighting protection."""

from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.smartbulb_mgmt.const import (
    COLOR_MODE_RGB,
    CONF_BULB_ENTITIES,
    CONF_COLOR_MODE,
    CONF_DEFAULT_BRIGHTNESS_PCT,
    CONF_HOLIDAY_CONTROL_ENTITY,
    CONF_HOLIDAY_ENTITY,
    CONF_OVERRIDE_HOLIDAY,
    CONF_PAUSE_HOLIDAY_ON_OFF,
    CONF_RGB_COLOR,
    CONF_SWITCH_ENTITY,
    CONF_TWO_WAY_SYNC,
    DOMAIN,
)
from homeassistant.core import HomeAssistant


async def test_switch_on_applies_color_when_holiday_done(hass: HomeAssistant) -> None:
    """Switch On applies configured RGB color and brightness when holiday is Done."""
    hass.states.async_set("switch.porch_switch", "off")
    hass.states.async_set("light.porch_bulb", "off")
    hass.states.async_set("sensor.holiday_lighting_status", "Done for tonight")

    light_on_calls = async_mock_service(hass, "light", "turn_on")
    async_mock_service(hass, "light", "turn_off")

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_SWITCH_ENTITY: "switch.porch_switch",
            CONF_BULB_ENTITIES: ["light.porch_bulb"],
            CONF_HOLIDAY_ENTITY: "sensor.holiday_lighting_status",
            CONF_TWO_WAY_SYNC: True,
            CONF_OVERRIDE_HOLIDAY: False,
            CONF_COLOR_MODE: COLOR_MODE_RGB,
            CONF_RGB_COLOR: [255, 128, 0],
            CONF_DEFAULT_BRIGHTNESS_PCT: 75,
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)

    hass.states.async_set("switch.porch_switch", "on")
    await hass.async_block_till_done(wait_background_tasks=True)

    assert len(light_on_calls) == 1
    assert light_on_calls[0].data["rgb_color"] == [255, 128, 0]
    assert light_on_calls[0].data["brightness_pct"] == 75


async def test_bulb_on_syncs_switch_without_bouncing(hass: HomeAssistant) -> None:
    """Holiday lighting turning on a bulb updates the switch without calling light.turn_on."""
    hass.states.async_set("switch.porch_switch", "off")
    hass.states.async_set("light.porch_bulb", "off")
    hass.states.async_set("sensor.holiday_lighting_status", "On")

    light_on_calls = async_mock_service(hass, "light", "turn_on")
    switch_on_calls = async_mock_service(hass, "switch", "turn_on")

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_SWITCH_ENTITY: "switch.porch_switch",
            CONF_BULB_ENTITIES: ["light.porch_bulb"],
            CONF_HOLIDAY_ENTITY: "sensor.holiday_lighting_status",
            CONF_TWO_WAY_SYNC: True,
            CONF_OVERRIDE_HOLIDAY: False,
            CONF_COLOR_MODE: COLOR_MODE_RGB,
            CONF_RGB_COLOR: [255, 255, 255],
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)

    hass.states.async_set("light.porch_bulb", "on")
    await hass.async_block_till_done(wait_background_tasks=True)

    assert len(switch_on_calls) == 1
    assert len(light_on_calls) == 0


async def test_manual_switch_off_pauses_holiday_when_configured(
    hass: HomeAssistant,
) -> None:
    """Manual switch Off turns off bulbs and optionally pauses holiday control entity."""
    hass.states.async_set("switch.porch_switch", "on")
    hass.states.async_set("light.porch_bulb", "on")
    hass.states.async_set("sensor.holiday_lighting_status", "On")
    hass.states.async_set("switch.holiday_lighting_enabled", "on")

    light_off_calls = async_mock_service(hass, "light", "turn_off")
    switch_off_calls = async_mock_service(hass, "switch", "turn_off")

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_SWITCH_ENTITY: "switch.porch_switch",
            CONF_BULB_ENTITIES: ["light.porch_bulb"],
            CONF_HOLIDAY_ENTITY: "sensor.holiday_lighting_status",
            CONF_HOLIDAY_CONTROL_ENTITY: "switch.holiday_lighting_enabled",
            CONF_PAUSE_HOLIDAY_ON_OFF: True,
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)

    hass.states.async_set("switch.porch_switch", "off")
    await hass.async_block_till_done(wait_background_tasks=True)

    assert len(light_off_calls) == 1
    assert any(
        call.data["entity_id"] == "switch.holiday_lighting_enabled"
        for call in switch_off_calls
    )
