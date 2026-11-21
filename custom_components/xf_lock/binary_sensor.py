"""小峰门锁二进制传感器实体。"""
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sn = entry.data["sn"][-4:]
    async_add_entities([
        XFLockBinary(coordinator, "online", "在线", BinarySensorDeviceClass.CONNECTIVITY, "mdi:wifi", sn),
        XFLockBinary(coordinator, "locked", "已上锁", BinarySensorDeviceClass.LOCK, "mdi:lock", sn),
        XFLockBinary(coordinator, "alarm", "告警", BinarySensorDeviceClass.PROBLEM, "mdi:alert", sn),
    ])


class XFLockBinary(CoordinatorEntity, BinarySensorEntity):
    def __init__(self, coordinator, key, name, device_class, icon, sn):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = "小峰门锁 " + name
        self._attr_device_class = device_class
        self._attr_icon = icon
        self._attr_unique_id = "xf_lock_%s_%s" % (sn, key)

    @property
    def is_on(self):
        return bool((self.coordinator.data or {}).get(self._key))
