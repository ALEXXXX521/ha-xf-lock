"""小峰门锁摄像头实体 —— 显示最近一次门铃抓拍图。

门锁是电池低功耗设备，实时直播不可行(需唤醒+3秒内拉流)，
因此这里呈现门铃按铃瞬间抓拍的快照，URL 由协调器定期刷新签名。
"""
import logging

from homeassistant.components.camera import Camera
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    sn = entry.data["sn"][-4:]
    async_add_entities([XFLockCamera(coordinator, sn)])


class XFLockCamera(CoordinatorEntity, Camera):
    def __init__(self, coordinator, sn):
        CoordinatorEntity.__init__(self, coordinator)
        Camera.__init__(self)
        self._attr_name = "小峰门锁摄像头"
        self._attr_unique_id = "xf_lock_%s_camera" % sn
        self._attr_icon = "mdi:doorbell-video"

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        return {
            "抓拍时间": (data.get("last_event") or "").replace("门铃", "").strip() or "暂无",
        }

    async def async_camera_image(self, width=None, height=None):
        url = (self.coordinator.data or {}).get("snapshot_url")
        if not url:
            return None
        try:
            session = async_get_clientsession(self.hass)
            async with session.get(url, timeout=15) as resp:
                if resp.status == 200:
                    return await resp.read()
        except Exception as exc:
            _LOGGER.debug("抓拍图拉取失败: %s", exc)
        return None
