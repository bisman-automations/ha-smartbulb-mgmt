"""Config flow for Smart Bulb Management."""

from __future__ import annotations

from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    BooleanSelector,
    ColorRGBSelector,
    ColorTempSelector,
    ColorTempSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    COLOR_MODE_NONE,
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
    DEFAULT_BRIGHTNESS_PCT,
    DEFAULT_COLOR_MODE,
    DEFAULT_COLOR_TEMP_KELVIN,
    DEFAULT_HOLIDAY_ENTITY,
    DEFAULT_OVERRIDE_HOLIDAY,
    DEFAULT_PAUSE_HOLIDAY_ON_OFF,
    DEFAULT_SYNC_BRIGHTNESS,
    DEFAULT_TWO_WAY_SYNC,
    DOMAIN,
)

COLOR_MODE_OPTIONS = [
    {"value": COLOR_MODE_NONE, "label": "Do not set color"},
    {"value": COLOR_MODE_RGB, "label": "RGB Color"},
    {"value": COLOR_MODE_TEMP, "label": "Color Temperature (Kelvin)"},
]


class SmartBulbMgmtConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Smart Bulb Management."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            switch_entity = user_input[CONF_SWITCH_ENTITY]
            await self.async_set_unique_id(switch_entity)
            self._abort_if_unique_id_configured()

            state = self.hass.states.get(switch_entity)
            title = state.name if state and state.name else switch_entity
            return self.async_create_entry(title=title, data=user_input)

        holiday_default = (
            DEFAULT_HOLIDAY_ENTITY
            if self.hass.states.get(DEFAULT_HOLIDAY_ENTITY) is not None
            else vol.UNDEFINED
        )

        fields: dict[Any, Any] = {
            vol.Required(CONF_SWITCH_ENTITY): EntitySelector(
                EntitySelectorConfig(domain=["switch", "light"])
            ),
            vol.Required(CONF_BULB_ENTITIES): EntitySelector(
                EntitySelectorConfig(domain="light", multiple=True)
            ),
        }
        if holiday_default is not vol.UNDEFINED:
            fields[vol.Optional(CONF_HOLIDAY_ENTITY, default=holiday_default)] = (
                EntitySelector(
                    EntitySelectorConfig(
                        domain=["sensor", "binary_sensor", "switch", "input_boolean"]
                    )
                )
            )
        else:
            fields[vol.Optional(CONF_HOLIDAY_ENTITY)] = EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "binary_sensor", "switch", "input_boolean"]
                )
            )

        fields.update(
            {
                vol.Optional(CONF_HOLIDAY_CONTROL_ENTITY): EntitySelector(
                    EntitySelectorConfig(domain=["switch", "input_boolean"])
                ),
                vol.Optional(
                    CONF_PAUSE_HOLIDAY_ON_OFF, default=DEFAULT_PAUSE_HOLIDAY_ON_OFF
                ): BooleanSelector(),
                vol.Optional(
                    CONF_TWO_WAY_SYNC, default=DEFAULT_TWO_WAY_SYNC
                ): BooleanSelector(),
                vol.Optional(
                    CONF_SYNC_BRIGHTNESS, default=DEFAULT_SYNC_BRIGHTNESS
                ): BooleanSelector(),
                vol.Optional(
                    CONF_OVERRIDE_HOLIDAY, default=DEFAULT_OVERRIDE_HOLIDAY
                ): BooleanSelector(),
                vol.Optional(
                    CONF_COLOR_MODE, default=DEFAULT_COLOR_MODE
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=COLOR_MODE_OPTIONS,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(CONF_RGB_COLOR, default=[255, 255, 255]): ColorRGBSelector(),
                vol.Optional(
                    CONF_COLOR_TEMP_KELVIN, default=DEFAULT_COLOR_TEMP_KELVIN
                ): ColorTempSelector(
                    ColorTempSelectorConfig(unit="kelvin", min=2000, max=6500)
                ),
                vol.Optional(
                    CONF_DEFAULT_BRIGHTNESS_PCT, default=DEFAULT_BRIGHTNESS_PCT
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=100, step=1, mode=NumberSelectorMode.SLIDER
                    )
                ),
            }
        )

        return self.async_show_form(step_id="user", data_schema=vol.Schema(fields))

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> SmartBulbMgmtOptionsFlow:
        """Get the options flow for this handler."""
        return SmartBulbMgmtOptionsFlow(config_entry)


class SmartBulbMgmtOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Smart Bulb Management."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **self.config_entry.options}
        holiday_default = current.get(CONF_HOLIDAY_ENTITY)
        control_default = current.get(CONF_HOLIDAY_CONTROL_ENTITY)

        fields: dict[Any, Any] = {
            vol.Required(
                CONF_BULB_ENTITIES,
                default=current.get(CONF_BULB_ENTITIES, []),
            ): EntitySelector(EntitySelectorConfig(domain="light", multiple=True)),
        }

        if holiday_default:
            fields[vol.Optional(CONF_HOLIDAY_ENTITY, default=holiday_default)] = (
                EntitySelector(
                    EntitySelectorConfig(
                        domain=["sensor", "binary_sensor", "switch", "input_boolean"]
                    )
                )
            )
        else:
            fields[vol.Optional(CONF_HOLIDAY_ENTITY)] = EntitySelector(
                EntitySelectorConfig(
                    domain=["sensor", "binary_sensor", "switch", "input_boolean"]
                )
            )

        if control_default:
            fields[
                vol.Optional(CONF_HOLIDAY_CONTROL_ENTITY, default=control_default)
            ] = EntitySelector(EntitySelectorConfig(domain=["switch", "input_boolean"]))
        else:
            fields[vol.Optional(CONF_HOLIDAY_CONTROL_ENTITY)] = EntitySelector(
                EntitySelectorConfig(domain=["switch", "input_boolean"])
            )

        fields.update(
            {
                vol.Optional(
                    CONF_PAUSE_HOLIDAY_ON_OFF,
                    default=current.get(
                        CONF_PAUSE_HOLIDAY_ON_OFF, DEFAULT_PAUSE_HOLIDAY_ON_OFF
                    ),
                ): BooleanSelector(),
                vol.Optional(
                    CONF_TWO_WAY_SYNC,
                    default=current.get(CONF_TWO_WAY_SYNC, DEFAULT_TWO_WAY_SYNC),
                ): BooleanSelector(),
                vol.Optional(
                    CONF_SYNC_BRIGHTNESS,
                    default=current.get(CONF_SYNC_BRIGHTNESS, DEFAULT_SYNC_BRIGHTNESS),
                ): BooleanSelector(),
                vol.Optional(
                    CONF_OVERRIDE_HOLIDAY,
                    default=current.get(CONF_OVERRIDE_HOLIDAY, DEFAULT_OVERRIDE_HOLIDAY),
                ): BooleanSelector(),
                vol.Optional(
                    CONF_COLOR_MODE,
                    default=current.get(CONF_COLOR_MODE, DEFAULT_COLOR_MODE),
                ): SelectSelector(
                    SelectSelectorConfig(
                        options=COLOR_MODE_OPTIONS,
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Optional(
                    CONF_RGB_COLOR,
                    default=current.get(CONF_RGB_COLOR, [255, 255, 255]),
                ): ColorRGBSelector(),
                vol.Optional(
                    CONF_COLOR_TEMP_KELVIN,
                    default=current.get(
                        CONF_COLOR_TEMP_KELVIN, DEFAULT_COLOR_TEMP_KELVIN
                    ),
                ): ColorTempSelector(
                    ColorTempSelectorConfig(unit="kelvin", min=2000, max=6500)
                ),
                vol.Optional(
                    CONF_DEFAULT_BRIGHTNESS_PCT,
                    default=current.get(
                        CONF_DEFAULT_BRIGHTNESS_PCT, DEFAULT_BRIGHTNESS_PCT
                    ),
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=1, max=100, step=1, mode=NumberSelectorMode.SLIDER
                    )
                ),
            }
        )

        return self.async_show_form(step_id="init", data_schema=vol.Schema(fields))
