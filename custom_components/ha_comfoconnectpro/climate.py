from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.climate.const import (
    PRESET_AWAY,
    PRESET_BOOST,
    PRESET_HOME,
    PRESET_SLEEP,
)
from homeassistant.const import CONF_NAME, UnitOfTemperature
from homeassistant.core import callback

from .const import (
    ATTR_MANUFACTURER,
    C_STANDBY,
    C_SUPPLY_HUMIDITY,
    C_SUPPLY_TEMPERATURE,
    C_TEMPERATURE_PROFILE,
    C_VENTILATION_PRESET,
    DEFAULT_NAME,
    DOMAIN,
    MyClimateEntityDescription,
)
from .entity_common import HubBackedEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up climate entity from config entry."""
    hub_name = entry.options.get(CONF_NAME, entry.data[CONF_NAME])
    hub = hass.data[DOMAIN][hub_name]["hub"]
    device_info = {
        "identifiers": {(DOMAIN, entry.entry_id)},
        "name": DEFAULT_NAME,
        "manufacturer": ATTR_MANUFACTURER,
    }
    description = MyClimateEntityDescription(
        key="ventilation_climate",
        name="Climate",
        translation_key="ventilation_climate",
        supported_features=ClimateEntityFeature.PRESET_MODE,
    )
    async_add_entities([MyClimate(hub_name, hub, device_info, description)])


class MyClimate(HubBackedEntity, ClimateEntity):
    """Composite climate entity for the ComfoConnect PRO ventilation unit."""

    entity_description: MyClimateEntityDescription

    _PROFILE_TO_ACTION: dict[str, HVACAction] = {
        "comfort": HVACAction.FAN,
        "cool": HVACAction.COOLING,
        "warm": HVACAction.HEATING,
    }

    def __init__(self, platform_name, hub, device_info, description):
        super().__init__(platform_name, hub, device_info, description)
        self._attr_hvac_modes = [HVACMode.AUTO]
        self._attr_hvac_mode = HVACMode.AUTO
        self._attr_hvac_action = HVACAction.FAN
        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_supported_features = ClimateEntityFeature.PRESET_MODE
        self._attr_preset_modes = [PRESET_AWAY, PRESET_SLEEP, PRESET_HOME, PRESET_BOOST]
        self._attr_preset_mode = PRESET_HOME

    @callback
    def _on_hub_update(self) -> None:
        supply_temp = self._hub.data.get(C_SUPPLY_TEMPERATURE)
        if supply_temp is not None:
            self._attr_current_temperature = float(supply_temp)

        supply_hum = self._hub.data.get(C_SUPPLY_HUMIDITY)
        if supply_hum is not None:
            self._attr_current_humidity = int(supply_hum)

        if self._hub.data.get(C_STANDBY):
            self._attr_hvac_action = HVACAction.IDLE
        else:
            profile = self._hub.data.get(C_TEMPERATURE_PROFILE)
            if profile is not None:
                self._attr_hvac_action = self._PROFILE_TO_ACTION.get(
                    profile, HVACAction.FAN
                )

        preset = self._hub.data.get(C_VENTILATION_PRESET)
        if preset is not None:
            self._attr_preset_mode = preset

        self.async_write_ha_state()

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set ventilation preset."""
        self._attr_preset_mode = preset_mode
        await self._hub.write_entity_value(C_VENTILATION_PRESET, preset_mode)
