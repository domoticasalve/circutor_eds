from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_HOST, CONF_DEVICE_ID, SENSOR_TYPES
from .coordinator import CiructorCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: CiructorCoordinator = hass.data[DOMAIN][entry.entry_id]
    device_id = entry.data[CONF_DEVICE_ID]
    host = entry.data[CONF_HOST]

    entities = []
    for sensor_key, sensor_def in SENSOR_TYPES.items():
        if sensor_key in coordinator.data:
            entities.append(
                CiructorSensor(coordinator, entry, sensor_key, sensor_def, device_id, host)
            )
        else:
            _LOGGER.debug("Variable %s no encontrada en el XML, sensor omitido", sensor_key)

    async_add_entities(entities)


class CiructorSensor(CoordinatorEntity, SensorEntity):
    def __init__(
        self,
        coordinator: CiructorCoordinator,
        entry: ConfigEntry,
        sensor_key: str,
        sensor_def: tuple,
        device_id: str,
        host: str,
    ) -> None:
        super().__init__(coordinator)
        friendly_name, unit, device_class, state_class, icon = sensor_def

        self._sensor_key = sensor_key
        self._device_id = device_id
        self._attr_unique_id = f"{entry.entry_id}_{sensor_key}"
        self._attr_name = f"{device_id} {friendly_name}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_icon = icon
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Medidor {device_id}",
            manufacturer="Ciructor",
            model="CVM Energy Monitor",
            configuration_url=f"http://{host}",
        )

    @property
    def native_value(self):
        value = self.coordinator.data.get(self._sensor_key)
        if value is None:
            return None
        if isinstance(value, float):
            return round(value, 6)
        return value
