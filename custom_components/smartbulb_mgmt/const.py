"""Constants for the Smart Bulb Management integration."""

DOMAIN = "smartbulb_mgmt"

CONF_SWITCH_ENTITY = "switch_entity"
CONF_BULB_ENTITIES = "bulb_entities"
CONF_HOLIDAY_ENTITY = "holiday_entity"
CONF_HOLIDAY_CONTROL_ENTITY = "holiday_control_entity"
CONF_PAUSE_HOLIDAY_ON_OFF = "pause_holiday_on_off"
CONF_SYNC_BRIGHTNESS = "sync_brightness"
CONF_TWO_WAY_SYNC = "two_way_sync"
CONF_OVERRIDE_HOLIDAY = "override_holiday"
CONF_COLOR_MODE = "color_mode"
CONF_RGB_COLOR = "rgb_color"
CONF_COLOR_TEMP_KELVIN = "color_temp_kelvin"
CONF_DEFAULT_BRIGHTNESS_PCT = "default_brightness_pct"

COLOR_MODE_NONE = "none"
COLOR_MODE_RGB = "rgb"
COLOR_MODE_TEMP = "color_temp"

DEFAULT_HOLIDAY_ENTITY = "sensor.holiday_lighting_status"
DEFAULT_PAUSE_HOLIDAY_ON_OFF = False
DEFAULT_SYNC_BRIGHTNESS = True
DEFAULT_TWO_WAY_SYNC = True
DEFAULT_OVERRIDE_HOLIDAY = False
DEFAULT_COLOR_MODE = COLOR_MODE_NONE
DEFAULT_COLOR_TEMP_KELVIN = 2700
DEFAULT_BRIGHTNESS_PCT = 100
# Backstop for bulbs that report back without our context. Our own calls are
# recognised by their tracked Context first.
SYNC_COOLDOWN_SECONDS = 1.5

ISSUE_SWITCH_MISSING = "switch_missing"
ISSUE_BULBS_MISSING = "bulbs_missing"
