"""Tests for reconnects, slow bulbs, failed calls and unloading."""

import logging

import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_mock_service,
)

from custom_components.smartbulb_mgmt.const import (
    CONF_BULB_ENTITIES,
    CONF_SWITCH_ENTITY,
    CONF_TWO_WAY_SYNC,
    DOMAIN,
)
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError

SWITCH = "switch.porch_switch"
BULB_1 = "light.porch_bulb_1"
BULB_2 = "light.porch_bulb_2"


async def _setup(hass: HomeAssistant, **data) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=SWITCH,
        title="Porch",
        data={
            CONF_SWITCH_ENTITY: SWITCH,
            CONF_BULB_ENTITIES: [BULB_1, BULB_2],
            CONF_TWO_WAY_SYNC: True,
            **data,
        },
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    return entry


async def _settle(hass: HomeAssistant) -> None:
    await hass.async_block_till_done(wait_background_tasks=True)


@pytest.mark.parametrize("offline", [STATE_UNAVAILABLE, "unknown"])
async def test_switch_reconnecting_on_leaves_bulbs_alone(
    hass: HomeAssistant, offline: str
) -> None:
    """A switch that drops off and comes back On is not someone pressing it."""
    hass.states.async_set(SWITCH, "off")
    hass.states.async_set(BULB_1, "off")
    hass.states.async_set(BULB_2, "off")
    light_on = async_mock_service(hass, "light", "turn_on")
    light_off = async_mock_service(hass, "light", "turn_off")
    await _setup(hass)

    hass.states.async_set(SWITCH, offline)
    await _settle(hass)
    hass.states.async_set(SWITCH, "on")
    await _settle(hass)

    assert light_on == []
    assert light_off == []

    # The next real press still works.
    hass.states.async_set(SWITCH, "off")
    await _settle(hass)
    assert len(light_off) == 1


async def test_switch_first_appearing_leaves_bulbs_alone(hass: HomeAssistant) -> None:
    """A switch whose state first appears after setup doesn't turn the bulbs on."""
    hass.states.async_set(BULB_1, "off")
    hass.states.async_set(BULB_2, "off")
    light_on = async_mock_service(hass, "light", "turn_on")
    await _setup(hass)

    hass.states.async_set(SWITCH, "on")
    await _settle(hass)

    assert light_on == []


async def test_slow_bulb_report_does_not_flip_switch_back(
    hass: HomeAssistant,
) -> None:
    """Bulbs reporting our own call after the cooldown don't bounce to the switch."""
    hass.states.async_set(SWITCH, "on")
    hass.states.async_set(BULB_1, "on")
    hass.states.async_set(BULB_2, "on")
    light_off = async_mock_service(hass, "light", "turn_off")
    switch_on = async_mock_service(hass, "switch", "turn_on")
    entry = await _setup(hass)

    hass.states.async_set(SWITCH, "off")
    await _settle(hass)
    assert len(light_off) == 1

    # The cooldown has passed by the time a slow bulb reports; the other bulb
    # hasn't reported yet and still shows On.
    entry.runtime_data.ignore_bulbs_until = 0.0
    hass.states.async_set(BULB_1, "off", context=light_off[0].context)
    await _settle(hass)

    assert switch_on == []


async def test_bulb_change_from_elsewhere_still_updates_switch(
    hass: HomeAssistant,
) -> None:
    """A bulb turned on by something else still moves the switch."""
    hass.states.async_set(SWITCH, "off")
    hass.states.async_set(BULB_1, "off")
    hass.states.async_set(BULB_2, "off")
    switch_on = async_mock_service(hass, "switch", "turn_on")
    light_on = async_mock_service(hass, "light", "turn_on")
    await _setup(hass)

    hass.states.async_set(BULB_1, "on")
    await _settle(hass)

    assert len(switch_on) == 1
    # The passive switch update comes back with our context: no bounce.
    hass.states.async_set(SWITCH, "on", context=switch_on[0].context)
    await _settle(hass)
    assert light_on == []


async def test_failed_light_call_is_logged(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """A light call that fails shows up in the log instead of disappearing."""
    hass.states.async_set(SWITCH, "off")
    hass.states.async_set(BULB_1, "off")
    hass.states.async_set(BULB_2, "off")

    async def _fail(call: ServiceCall) -> None:
        raise HomeAssistantError("bulb offline")

    hass.services.async_register("light", "turn_on", _fail)
    await _setup(hass)

    with caplog.at_level(logging.WARNING, logger="custom_components.smartbulb_mgmt"):
        hass.states.async_set(SWITCH, "on")
        await _settle(hass)

    ours = [
        r.getMessage()
        for r in caplog.records
        if r.name.startswith("custom_components.smartbulb_mgmt")
    ]
    assert any("light.turn_on" in m and "bulb offline" in m for m in ours)


async def test_missing_light_service_is_logged(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """A missing light service is logged too."""
    hass.states.async_set(SWITCH, "on")
    hass.states.async_set(BULB_1, "on")
    hass.states.async_set(BULB_2, "on")
    await _setup(hass)

    with caplog.at_level(logging.WARNING, logger="custom_components.smartbulb_mgmt"):
        hass.states.async_set(SWITCH, "off")
        await _settle(hass)

    ours = [
        r.getMessage()
        for r in caplog.records
        if r.name.startswith("custom_components.smartbulb_mgmt")
    ]
    assert any("light.turn_off" in m for m in ours)


async def test_unload_stops_syncing(hass: HomeAssistant) -> None:
    """After unloading, switch changes no longer reach the bulbs."""
    hass.states.async_set(SWITCH, "off")
    hass.states.async_set(BULB_1, "off")
    hass.states.async_set(BULB_2, "off")
    light_on = async_mock_service(hass, "light", "turn_on")
    entry = await _setup(hass)

    assert await hass.config_entries.async_unload(entry.entry_id)
    hass.states.async_set(SWITCH, "on")
    await _settle(hass)

    assert light_on == []
