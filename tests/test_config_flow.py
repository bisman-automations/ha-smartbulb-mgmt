"""Tests for Smart Bulb Management config and options flow."""

from unittest.mock import patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smartbulb_mgmt.const import (
    COLOR_MODE_RGB,
    CONF_BULB_ENTITIES,
    CONF_COLOR_MODE,
    CONF_DEFAULT_BRIGHTNESS_PCT,
    CONF_HOLIDAY_ENTITY,
    CONF_RGB_COLOR,
    CONF_SWITCH_ENTITY,
    DOMAIN,
)
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


async def test_user_flow_creates_entry(hass: HomeAssistant) -> None:
    """Test creating a config entry via the UI flow."""
    hass.states.async_set("switch.porch_switch", "off")
    hass.states.async_set("light.porch_bulb", "off")
    hass.states.async_set("sensor.holiday_lighting_status", "Done for tonight")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    with patch("custom_components.smartbulb_mgmt.async_setup_entry", return_value=True):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_SWITCH_ENTITY: "switch.porch_switch",
                CONF_BULB_ENTITIES: ["light.porch_bulb"],
                CONF_HOLIDAY_ENTITY: "sensor.holiday_lighting_status",
                CONF_COLOR_MODE: COLOR_MODE_RGB,
                CONF_RGB_COLOR: [255, 180, 100],
                CONF_DEFAULT_BRIGHTNESS_PCT: 80,
            },
        )

    assert result2["type"] is FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_SWITCH_ENTITY] == "switch.porch_switch"


async def test_duplicate_switch_aborts(hass: HomeAssistant) -> None:
    """Test that configuring the same switch twice aborts."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="switch.porch_switch",
        data={
            CONF_SWITCH_ENTITY: "switch.porch_switch",
            CONF_BULB_ENTITIES: ["light.porch_bulb"],
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SWITCH_ENTITY: "switch.porch_switch",
            CONF_BULB_ENTITIES: ["light.porch_bulb"],
        },
    )
    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"


async def test_reconfigure_changes_switch(hass: HomeAssistant) -> None:
    """Reconfigure points the entry at another switch and keeps the bulbs."""
    hass.states.async_set("switch.porch_switch", "off", {"friendly_name": "Porch"})
    hass.states.async_set(
        "light.porch_dimmer", "off", {"friendly_name": "Porch Dimmer"}
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="switch.porch_switch",
        title="Porch",
        data={
            CONF_SWITCH_ENTITY: "switch.porch_switch",
            CONF_BULB_ENTITIES: ["light.porch_bulb"],
        },
    )
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with patch("custom_components.smartbulb_mgmt.async_setup_entry", return_value=True):
        result2 = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_SWITCH_ENTITY: "light.porch_dimmer"}
        )
        await hass.async_block_till_done()

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "reconfigure_successful"
    assert entry.data[CONF_SWITCH_ENTITY] == "light.porch_dimmer"
    assert entry.data[CONF_BULB_ENTITIES] == ["light.porch_bulb"]
    assert entry.unique_id == "light.porch_dimmer"
    assert entry.title == "Porch Dimmer"


async def test_reconfigure_keeps_custom_title(hass: HomeAssistant) -> None:
    """A title the user chose isn't replaced by the new switch's name."""
    hass.states.async_set(
        "light.porch_dimmer", "off", {"friendly_name": "Porch Dimmer"}
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="switch.porch_switch",
        title="Front door lights",
        data={
            CONF_SWITCH_ENTITY: "switch.porch_switch",
            CONF_BULB_ENTITIES: ["light.porch_bulb"],
        },
    )
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    with patch("custom_components.smartbulb_mgmt.async_setup_entry", return_value=True):
        await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_SWITCH_ENTITY: "light.porch_dimmer"}
        )
        await hass.async_block_till_done()

    assert entry.title == "Front door lights"


async def test_reconfigure_to_configured_switch_aborts(hass: HomeAssistant) -> None:
    """Reconfigure can't pick a switch another entry already uses."""
    data = {CONF_BULB_ENTITIES: ["light.porch_bulb"]}
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="switch.porch_switch",
        data={CONF_SWITCH_ENTITY: "switch.porch_switch", **data},
    )
    entry.add_to_hass(hass)
    MockConfigEntry(
        domain=DOMAIN,
        unique_id="switch.garage_switch",
        data={CONF_SWITCH_ENTITY: "switch.garage_switch", **data},
    ).add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_SWITCH_ENTITY: "switch.garage_switch"}
    )

    assert result2["type"] is FlowResultType.ABORT
    assert result2["reason"] == "already_configured"
    assert entry.data[CONF_SWITCH_ENTITY] == "switch.porch_switch"
