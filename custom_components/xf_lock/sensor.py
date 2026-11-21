"""小峰门锁传感器实体。"""
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sn = entry.data["sn"][-4:]
    async_add_entities([
        XFLockTextSensor(coordinator, "last_event", "最近事件", "mdi:history", sn),
        XFLockTextSensor(coordinator, "last_unlock", "开锁方式", "mdi:key", sn),
        XFLockSnapshotSensor(coordinator, sn),
    ])


class XFLockTextSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, key, name, icon, sn):
        super().__init__(coordinator)
        self._key = key
        self._attr_name = "小峰门锁 " + name
        self._attr_icon = icon
        self._attr_unique_id = "xf_lock_%s_%s" % (sn, key)

    @property
    def native_value(self):
        return (self.coordinator.data or {}).get(self._key)


class XFLockSnapshotSensor(CoordinatorEntity, SensorEntity):
    """抓拍图 URL 传感器(供摄像头实体模板引用)。"""

    def __init__(self, coordinator, sn):
        super().__init__(coordinator)
        self._attr_name = "小峰门锁 抓拍图URL"
        self._attr_icon = "mdi:camera"
        self._attr_unique_id = "xf_lock_%s_snapshot_url" % sn
        self._attr_entity_registry_enabled_default = True

    @property
    def native_value(self):
        return (self.coordinator.data or {}).get("snapshot_url")
