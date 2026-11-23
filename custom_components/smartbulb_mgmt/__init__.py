"""Smart Bulb Management integration for Home Assistant."""

from __future__ import annotations

from collections import deque
import logging
import time
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, STATE_ON, STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import Context, Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    COLOR_MODE_RGB,
    COLOR_MODE_TEMP,
    CONF_BULB_ENTITIES,
    CONF_COLOR_MODE,
    CONF_COLOR_TEMP_KELVIN,
    CONF_DEFAULT_BRIGHTNESS_PCT,
    CONF_HOLIDAY_CONTROL_ENTITY,
    CONF_HOLIDAY_ENTITY,
    CONF_OVERRIDE_HOLIDAY,
    CONF_PAUSE_HOLIDAY_ON_OFF,
    CONF_RGB_COLOR,
    CONF_SWITCH_ENTITY,
    CONF_SYNC_BRIGHTNESS,
    CONF_TWO_WAY_SYNC,
    DEFAULT_COLOR_MODE,
    DEFAULT_OVERRIDE_HOLIDAY,
    DEFAULT_PAUSE_HOLIDAY_ON_OFF,
    DEFAULT_SYNC_BRIGHTNESS,
    DEFAULT_TWO_WAY_SYNC,
    DOMAIN,
    SYNC_COOLDOWN_SECONDS,
)

_LOGGER = logging.getLogger(__name__)


def _is_holiday_running(hass: HomeAssistant, holiday_entity: str | None) -> bool:
    """Return True if the configured holiday lighting entity is actively On."""
    if not holiday_entity:
        return False
    state = hass.states.get(holiday_entity)
    if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
        return False
    return state.state.strip().lower() == "on"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Smart Bulb Management from a config entry."""
    config = {**entry.data, **entry.options}
    switch_entity: str = config[CONF_SWITCH_ENTITY]
    bulb_entities: list[str] = config[CONF_BULB_ENTITIES]
    holiday_entity: str | None = config.get(CONF_HOLIDAY_ENTITY)
    holiday_control_entity: str | None = config.get(CONF_HOLIDAY_CONTROL_ENTITY)
    pause_holiday_on_off: bool = config.get(
        CONF_PAUSE_HOLIDAY_ON_OFF, DEFAULT_PAUSE_HOLIDAY_ON_OFF
    )
    sync_brightness: bool = config.get(CONF_SYNC_BRIGHTNESS, DEFAULT_SYNC_BRIGHTNESS)
    two_way_sync: bool = config.get(CONF_TWO_WAY_SYNC, DEFAULT_TWO_WAY_SYNC)
    override_holiday: bool = config.get(CONF_OVERRIDE_HOLIDAY, DEFAULT_OVERRIDE_HOLIDAY)
    color_mode: str = config.get(CONF_COLOR_MODE, DEFAULT_COLOR_MODE)
    rgb_color: list[int] | None = config.get(CONF_RGB_COLOR)
    color_temp_kelvin: int | None = config.get(CONF_COLOR_TEMP_KELVIN)
    default_brightness_pct: int | None = config.get(CONF_DEFAULT_BRIGHTNESS_PCT)

    own_context_ids: deque[str] = deque(maxlen=50)
    ignore_switch_until = 0.0
    ignore_bulbs_until = 0.0

    @callback
    def _handle_switch_change(event: Event) -> None:
        """Mirror manual switch changes to target smart bulbs without bouncing."""
        nonlocal ignore_bulbs_until

        ctx = event.context
        if ctx and (ctx.id in own_context_ids or ctx.parent_id in own_context_ids):
            return

        if time.monotonic() < ignore_switch_until:
            return

        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        state_changed = old_state is None or old_state.state != new_state.state
        brightness_changed = (
            sync_brightness
            and new_state.state == STATE_ON
            and old_state is not None
            and old_state.attributes.get("brightness")
            != new_state.attributes.get("brightness")
        )
        if not state_changed and not brightness_changed:
            return

        ignore_bulbs_until = time.monotonic() + SYNC_COOLDOWN_SECONDS
        holiday_running = _is_holiday_running(hass, holiday_entity)

        if new_state.state == STATE_ON:
            if holiday_running and not override_holiday:
                off_bulbs = [
                    entity_id
                    for entity_id in bulb_entities
                    if (st := hass.states.get(entity_id)) is None
                    or st.state != STATE_ON
                ]
                if not off_bulbs:
                    return
                hass.async_create_task(
                    hass.services.async_call(
                        "light", "turn_on", {ATTR_ENTITY_ID: off_bulbs}
                    )
                )
                return

            service_data: dict[str, Any] = {ATTR_ENTITY_ID: bulb_entities}
            brightness = new_state.attributes.get("brightness")
            if sync_brightness and brightness is not None:
                service_data["brightness"] = brightness
            elif default_brightness_pct is not None:
                service_data["brightness_pct"] = int(default_brightness_pct)

            if color_mode == COLOR_MODE_RGB and rgb_color:
                service_data["rgb_color"] = [int(c) for c in rgb_color]
            elif color_mode == COLOR_MODE_TEMP and color_temp_kelvin is not None:
                service_data["color_temp_kelvin"] = int(color_temp_kelvin)

            hass.async_create_task(
                hass.services.async_call("light", "turn_on", service_data)
            )
        else:
            hass.async_create_task(
                hass.services.async_call(
                    "light", "turn_off", {ATTR_ENTITY_ID: bulb_entities}
                )
            )
            if (
                holiday_running
                and pause_holiday_on_off
                and holiday_control_entity
            ):
                control_domain = holiday_control_entity.split(".")[0]
                hass.async_create_task(
                    hass.services.async_call(
                        control_domain,
                        "turn_off",
                        {ATTR_ENTITY_ID: holiday_control_entity},
                    )
                )

    @callback
    def _handle_bulb_change(event: Event) -> None:
        """Passively mirror bulb On/Off state to the switch without bouncing."""
        nonlocal ignore_switch_until

        if time.monotonic() < ignore_bulbs_until:
            return

        new_state = event.data.get("new_state")
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return

        any_bulb_on = any(
            (st := hass.states.get(entity_id)) is not None and st.state == STATE_ON
            for entity_id in bulb_entities
        )

        switch_state = hass.states.get(switch_entity)
        if switch_state and (switch_state.state == STATE_ON) == any_bulb_on:
            return

        ctx = Context()
        own_context_ids.append(ctx.id)
        ignore_switch_until = time.monotonic() + SYNC_COOLDOWN_SECONDS

        switch_domain = switch_entity.split(".")[0]
        service = "turn_on" if any_bulb_on else "turn_off"
        hass.async_create_task(
            hass.services.async_call(
                switch_domain,
                service,
                {ATTR_ENTITY_ID: switch_entity},
                context=ctx,
            )
        )

    unsub_switch = async_track_state_change_event(
        hass, [switch_entity], _handle_switch_change
    )
    unsubscribers = [unsub_switch]

    if two_way_sync and bulb_entities:
        unsub_bulbs = async_track_state_change_event(
            hass, bulb_entities, _handle_bulb_change
        )
        unsubscribers.append(unsub_bulbs)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = unsubscribers
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    _LOGGER.debug(
        "Initialized Smart Bulb Management: %s -> %s (holiday=%s)",
        switch_entity,
        bulb_entities,
        holiday_entity,
    )
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unsubscribers = hass.data.get(DOMAIN, {}).pop(entry.entry_id, [])
    for unsub in unsubscribers:
        unsub()
    return True
