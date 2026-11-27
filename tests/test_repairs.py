"""Tests for the repairs raised when the switch or bulbs are deleted."""

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.smartbulb_mgmt.const import (
    CONF_BULB_ENTITIES,
    CONF_SWITCH_ENTITY,
    DOMAIN,
    ISSUE_BULBS_MISSING,
    ISSUE_SWITCH_MISSING,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er, issue_registry as ir

SWITCH = "switch.porch_switch"
BULB = "light.porch_bulb"
GONE = "light.old_bulb"


async def _setup(hass: HomeAssistant, bulbs: list[str]) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=SWITCH,
        title="Porch",
        data={CONF_SWITCH_ENTITY: SWITCH, CONF_BULB_ENTITIES: bulbs},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


def _issue(hass: HomeAssistant, entry: MockConfigEntry, kind: str):
    return ir.async_get(hass).async_get_issue(DOMAIN, f"{entry.entry_id}_{kind}")


async def test_missing_bulb_raises_repair(hass: HomeAssistant) -> None:
    """A bulb that doesn't exist at startup gets a repair naming it."""
    hass.states.async_set(SWITCH, "off")
    hass.states.async_set(BULB, "off")
    entry = await _setup(hass, [BULB, GONE])

    issue = _issue(hass, entry, ISSUE_BULBS_MISSING)
    assert issue is not None
    assert issue.translation_placeholders["entities"] == GONE
    assert _issue(hass, entry, ISSUE_SWITCH_MISSING) is None


async def test_all_present_raises_nothing(hass: HomeAssistant) -> None:
    """No repairs when the switch and bulbs exist."""
    hass.states.async_set(SWITCH, "off")
    hass.states.async_set(BULB, "off")
    entry = await _setup(hass, [BULB])

    assert _issue(hass, entry, ISSUE_BULBS_MISSING) is None
    assert _issue(hass, entry, ISSUE_SWITCH_MISSING) is None


async def test_deleted_switch_raises_repair_until_it_returns(
    hass: HomeAssistant,
) -> None:
    """Deleting the switch raises a repair; adding it back clears it."""
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "switch", "test", "porch", suggested_object_id="porch_switch"
    )
    hass.states.async_set(BULB, "off")
    entry = await _setup(hass, [BULB])
    assert _issue(hass, entry, ISSUE_SWITCH_MISSING) is None

    registry.async_remove(SWITCH)
    await hass.async_block_till_done()
    assert _issue(hass, entry, ISSUE_SWITCH_MISSING) is not None

    registry.async_get_or_create(
        "switch", "test", "porch", suggested_object_id="porch_switch"
    )
    await hass.async_block_till_done()
    assert _issue(hass, entry, ISSUE_SWITCH_MISSING) is None


async def test_renamed_bulb_raises_repair(hass: HomeAssistant) -> None:
    """Renaming a bulb's entity ID leaves the old one missing."""
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "light", "test", "porch", suggested_object_id="porch_bulb"
    )
    hass.states.async_set(SWITCH, "off")
    entry = await _setup(hass, [BULB])

    registry.async_update_entity(BULB, new_entity_id="light.front_bulb")
    await hass.async_block_till_done()

    issue = _issue(hass, entry, ISSUE_BULBS_MISSING)
    assert issue is not None
    assert issue.translation_placeholders["entities"] == BULB


async def test_removing_entry_clears_repairs(hass: HomeAssistant) -> None:
    """Deleting the entry removes its repairs."""
    hass.states.async_set(SWITCH, "off")
    entry = await _setup(hass, [GONE])
    assert _issue(hass, entry, ISSUE_BULBS_MISSING) is not None

    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert _issue(hass, entry, ISSUE_BULBS_MISSING) is None
