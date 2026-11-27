"""Smart Bulb Management integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir

from .const import DOMAIN, ISSUE_BULBS_MISSING, ISSUE_SWITCH_MISSING
from .sync import SmartBulbSync, issue_id

_LOGGER = logging.getLogger(__name__)

type SmartBulbConfigEntry = ConfigEntry[SmartBulbSync]


async def async_setup_entry(hass: HomeAssistant, entry: SmartBulbConfigEntry) -> bool:
    """Set up Smart Bulb Management from a config entry."""
    sync = SmartBulbSync(hass, entry)
    entry.runtime_data = sync
    for unsub in sync.async_start():
        entry.async_on_unload(unsub)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    _LOGGER.debug(
        "Initialized Smart Bulb Management: %s -> %s (holiday=%s)",
        sync.switch_entity,
        sync.bulb_entities,
        sync.holiday_entity,
    )
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: SmartBulbConfigEntry) -> None:
    """Reload the config entry when it changes."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: SmartBulbConfigEntry) -> bool:
    """Unload a config entry."""
    return True


async def async_remove_entry(hass: HomeAssistant, entry: SmartBulbConfigEntry) -> None:
    """Remove this entry's repairs when it is deleted."""
    for kind in (ISSUE_SWITCH_MISSING, ISSUE_BULBS_MISSING):
        ir.async_delete_issue(hass, DOMAIN, issue_id(entry.entry_id, kind))
