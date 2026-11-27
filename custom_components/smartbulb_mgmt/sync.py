"""Switch and bulb sync for Smart Bulb Management."""

from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
import logging
from time import monotonic
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_ENTITY_ID,
    STATE_ON,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
)
from homeassistant.core import Context, Event, HomeAssistant, State, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er, issue_registry as ir
from homeassistant.helpers.event import (
    async_track_entity_registry_updated_event,
    async_track_state_change_event,
)
from homeassistant.helpers.start import async_at_started

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
    ISSUE_BULBS_MISSING,
    ISSUE_SWITCH_MISSING,
    SYNC_COOLDOWN_SECONDS,
)

_LOGGER = logging.getLogger(__name__)

# How many of our own contexts to remember. Each switch change or passive
# switch update adds one; bulbs report back within seconds, so 50 is plenty.
_OWN_CONTEXTS = 50

_NOT_REAL = (STATE_UNAVAILABLE, STATE_UNKNOWN)


def _is_real(state: State | None) -> bool:
    """Return True for a state that reflects the device (not missing or offline)."""
    return state is not None and state.state not in _NOT_REAL


def issue_id(entry_id: str, kind: str) -> str:
    """Return the repair issue ID for one config entry."""
    return f"{entry_id}_{kind}"


@dataclass
class SmartBulbSync:
    """Mirror a smart-bulb-mode switch to its bulbs, and bulbs back to the switch."""

    hass: HomeAssistant
    entry: ConfigEntry
    own_context_ids: deque[str] = field(
        default_factory=lambda: deque(maxlen=_OWN_CONTEXTS)
    )
    missing: set[str] = field(default_factory=set)
    ignore_switch_until: float = 0.0
    ignore_bulbs_until: float = 0.0

    def __post_init__(self) -> None:
        """Read the entry's settings."""
        config = {**self.entry.data, **self.entry.options}
        self.switch_entity: str = config[CONF_SWITCH_ENTITY]
        self.bulb_entities: list[str] = list(config[CONF_BULB_ENTITIES])
        self.holiday_entity: str | None = config.get(CONF_HOLIDAY_ENTITY)
        self.holiday_control_entity: str | None = config.get(
            CONF_HOLIDAY_CONTROL_ENTITY
        )
        self.pause_holiday_on_off: bool = config.get(
            CONF_PAUSE_HOLIDAY_ON_OFF, DEFAULT_PAUSE_HOLIDAY_ON_OFF
        )
        self.sync_brightness: bool = config.get(
            CONF_SYNC_BRIGHTNESS, DEFAULT_SYNC_BRIGHTNESS
        )
        self.two_way_sync: bool = config.get(CONF_TWO_WAY_SYNC, DEFAULT_TWO_WAY_SYNC)
        self.override_holiday: bool = config.get(
            CONF_OVERRIDE_HOLIDAY, DEFAULT_OVERRIDE_HOLIDAY
        )
        self.color_mode: str = config.get(CONF_COLOR_MODE, DEFAULT_COLOR_MODE)
        self.rgb_color: list[int] | None = config.get(CONF_RGB_COLOR)
        self.color_temp_kelvin: int | None = config.get(CONF_COLOR_TEMP_KELVIN)
        self.default_brightness_pct: int | None = config.get(
            CONF_DEFAULT_BRIGHTNESS_PCT
        )

    # Setup ---------------------------------------------------------------

    @callback
    def async_start(self) -> list[Callable[[], None]]:
        """Start listening; return the callbacks that stop it."""
        unsubs = [
            async_track_state_change_event(
                self.hass, [self.switch_entity], self._handle_switch_change
            ),
            async_track_entity_registry_updated_event(
                self.hass, self.watched_entities, self._handle_registry_update
            ),
            async_at_started(self.hass, self._async_check_missing),
        ]
        if self.two_way_sync and self.bulb_entities:
            unsubs.append(
                async_track_state_change_event(
                    self.hass, self.bulb_entities, self._handle_bulb_change
                )
            )
        return unsubs

    @property
    def watched_entities(self) -> list[str]:
        """Return the switch and bulbs: the entities a repair is raised for."""
        return [self.switch_entity, *self.bulb_entities]

    # Helpers -------------------------------------------------------------

    def is_holiday_running(self) -> bool:
        """Return True if the configured holiday lighting entity is actively On."""
        if not self.holiday_entity:
            return False
        state = self.hass.states.get(self.holiday_entity)
        if not _is_real(state):
            return False
        return state.state.strip().lower() == "on"

    def _new_context(self) -> Context:
        """Return a context for one of our own calls, and remember it."""
        context = Context()
        self.own_context_ids.append(context.id)
        return context

    def _is_own(self, context: Context | None) -> bool:
        """Return True when an event was caused by one of our own calls."""
        return context is not None and (
            context.id in self.own_context_ids
            or context.parent_id in self.own_context_ids
        )

    @callback
    def _call(
        self, domain: str, service: str, data: dict[str, Any], context: Context
    ) -> None:
        """Call a service in the background and log it if it fails."""
        self.entry.async_create_background_task(
            self.hass,
            self._async_call(domain, service, data, context),
            f"{DOMAIN} {domain}.{service}",
        )

    async def _async_call(
        self, domain: str, service: str, data: dict[str, Any], context: Context
    ) -> None:
        try:
            await self.hass.services.async_call(
                domain, service, data, blocking=True, context=context
            )
        except (HomeAssistantError, vol.Invalid) as err:
            _LOGGER.warning(
                "%s.%s for %s failed: %s",
                domain,
                service,
                data.get(ATTR_ENTITY_ID),
                err,
            )

    # Switch -> bulbs -----------------------------------------------------

    @callback
    def _handle_switch_change(self, event: Event) -> None:
        """Mirror manual switch changes to the bulbs without bouncing."""
        if self._is_own(event.context):
            return
        if monotonic() < self.ignore_switch_until:
            return

        new_state: State | None = event.data.get("new_state")
        old_state: State | None = event.data.get("old_state")
        # Only a change between real states is someone using the switch. A
        # switch that comes back from unavailable (or first appears) is just
        # reporting where it already was.
        if not _is_real(new_state) or not _is_real(old_state):
            return

        state_changed = old_state.state != new_state.state
        brightness_changed = (
            self.sync_brightness
            and new_state.state == STATE_ON
            and old_state.attributes.get("brightness")
            != new_state.attributes.get("brightness")
        )
        if not state_changed and not brightness_changed:
            return

        self.ignore_bulbs_until = monotonic() + SYNC_COOLDOWN_SECONDS
        if new_state.state == STATE_ON:
            self._turn_bulbs_on(new_state)
        else:
            self._turn_bulbs_off()

    def _turn_bulbs_on(self, switch_state: State) -> None:
        if self.is_holiday_running() and not self.override_holiday:
            # Holiday lighting owns the colors: only switch on bulbs that are off.
            off_bulbs = [
                entity_id
                for entity_id in self.bulb_entities
                if (st := self.hass.states.get(entity_id)) is None
                or st.state != STATE_ON
            ]
            if off_bulbs:
                self._call(
                    "light",
                    "turn_on",
                    {ATTR_ENTITY_ID: off_bulbs},
                    self._new_context(),
                )
            return

        data: dict[str, Any] = {ATTR_ENTITY_ID: self.bulb_entities}
        brightness = switch_state.attributes.get("brightness")
        if self.sync_brightness and brightness is not None:
            data["brightness"] = brightness
        elif self.default_brightness_pct is not None:
            data["brightness_pct"] = int(self.default_brightness_pct)

        if self.color_mode == COLOR_MODE_RGB and self.rgb_color:
            data["rgb_color"] = [int(c) for c in self.rgb_color]
        elif self.color_mode == COLOR_MODE_TEMP and self.color_temp_kelvin is not None:
            data["color_temp_kelvin"] = int(self.color_temp_kelvin)

        self._call("light", "turn_on", data, self._new_context())

    def _turn_bulbs_off(self) -> None:
        context = self._new_context()
        self._call("light", "turn_off", {ATTR_ENTITY_ID: self.bulb_entities}, context)
        if (
            self.pause_holiday_on_off
            and self.holiday_control_entity
            and self.is_holiday_running()
        ):
            self._call(
                self.holiday_control_entity.split(".")[0],
                "turn_off",
                {ATTR_ENTITY_ID: self.holiday_control_entity},
                context,
            )

    # Bulbs -> switch -----------------------------------------------------

    @callback
    def _handle_bulb_change(self, event: Event) -> None:
        """Passively mirror bulb On/Off to the switch without bouncing."""
        # Bulbs reporting back after our own light call. The context catches
        # slow bulbs (Zigbee groups, cloud bulbs) that report after the timer.
        if self._is_own(event.context):
            return
        if monotonic() < self.ignore_bulbs_until:
            return
        if not _is_real(event.data.get("new_state")):
            return

        any_bulb_on = any(
            (st := self.hass.states.get(entity_id)) is not None and st.state == STATE_ON
            for entity_id in self.bulb_entities
        )
        switch_state = self.hass.states.get(self.switch_entity)
        if switch_state and (switch_state.state == STATE_ON) == any_bulb_on:
            return

        self.ignore_switch_until = monotonic() + SYNC_COOLDOWN_SECONDS
        self._call(
            self.switch_entity.split(".")[0],
            "turn_on" if any_bulb_on else "turn_off",
            {ATTR_ENTITY_ID: self.switch_entity},
            self._new_context(),
        )

    # Repairs -------------------------------------------------------------

    @callback
    def _async_check_missing(self, _hass: HomeAssistant | None = None) -> None:
        """Once Home Assistant has started, flag entities that no longer exist."""
        registry = er.async_get(self.hass)
        self.missing = {
            entity_id
            for entity_id in self.watched_entities
            if registry.async_get(entity_id) is None
            and self.hass.states.get(entity_id) is None
        }
        self._async_update_issues()

    @callback
    def _handle_registry_update(self, event: Event) -> None:
        """Follow the switch and bulbs being deleted, renamed or added back."""
        data = event.data
        action = data["action"]
        if action == "remove":
            self.missing.add(data["entity_id"])
        elif action == "create":
            self.missing.discard(data["entity_id"])
        elif action == "update" and (old := data.get("old_entity_id")):
            if old in self.watched_entities:
                self.missing.add(old)
            self.missing.discard(data["entity_id"])
        else:
            return
        self._async_update_issues()

    @callback
    def _async_update_issues(self) -> None:
        entry = self.entry
        placeholders = {"title": entry.title}
        if self.switch_entity in self.missing:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id(entry.entry_id, ISSUE_SWITCH_MISSING),
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_SWITCH_MISSING,
                translation_placeholders={
                    **placeholders,
                    "entity": self.switch_entity,
                },
            )
        else:
            ir.async_delete_issue(
                self.hass, DOMAIN, issue_id(entry.entry_id, ISSUE_SWITCH_MISSING)
            )

        missing_bulbs = [e for e in self.bulb_entities if e in self.missing]
        if missing_bulbs:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                issue_id(entry.entry_id, ISSUE_BULBS_MISSING),
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key=ISSUE_BULBS_MISSING,
                translation_placeholders={
                    **placeholders,
                    "entities": ", ".join(missing_bulbs),
                },
            )
        else:
            ir.async_delete_issue(
                self.hass, DOMAIN, issue_id(entry.entry_id, ISSUE_BULBS_MISSING)
            )
