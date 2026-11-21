"""小峰门锁集成入口。"""
import asyncio
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.config_entries import ConfigEntry

from .api import fetch_all
from .const import (
    DOMAIN, CONF_UUID, CONF_APP_KEY, CONF_APP_SECRET, CONF_MOVE_CARD,
    CONF_SN, CONF_ENDPOINT, CONF_SCAN_INTERVAL, DEFAULT_ENDPOINT,
    DEFAULT_SCAN_INTERVAL, LEGACY_ENTITIES,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "camera"]


def _build_cfg(entry):
    d = entry.data
    return {
        "uuid": d[CONF_UUID],
        "app_key": d[CONF_APP_KEY],
        "app_secret": d[CONF_APP_SECRET],
        "move_card": int(d[CONF_MOVE_CARD]),
        "sn": d[CONF_SN],
        "endpoint": d.get(CONF_ENDPOINT, DEFAULT_ENDPOINT),
    }


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    cfg = _build_cfg(entry)
    interval = entry.options.get(CONF_SCAN_INTERVAL,
                                 entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

    coordinator = XFLockCoordinator(hass, cfg, interval)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return ok


async def _async_reload(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)


class XFLockCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, cfg, interval):
        super().__init__(hass, _LOGGER, name="小峰门锁", update_interval=None)
        self.cfg = cfg
        self.interval = interval
        self.update_interval = __import__("datetime").timedelta(seconds=interval)
        self._token = None
        self._token_saved = 0.0
        self._warned = False

    async def _async_update_data(self):
        try:
            state, self._token, self._token_saved = await self.hass.async_add_executor_job(
                fetch_all, self.cfg, self._token, self._token_saved
            )
            self._warned = False
        except Exception as exc:
            if not self._warned:
                _LOGGER.warning("小峰门锁刷新失败: %s", exc)
                self._warned = True
            if self.data:
                return self.data  # 保留上次成功数据
            raise UpdateFailed(str(exc))

        # 兼容现有 helper 实体：存在则同步写入，保证 3D 页面/自动化无需改动
        await self._sync_legacy(state)
        return state

    async def _sync_legacy(self, state):
        mapping = [
            ("locked", "input_boolean", state["locked"]),
            ("online", "input_boolean", state["online"]),
            ("alarm", "input_boolean", state["alarm"]),
            ("event", "input_text", state["last_event"]),
            ("unlock", "input_text", state["last_unlock"]),
            ("snapshot", "input_text", state["snapshot_url"]),
        ]
        for key, domain, value in mapping:
            entity = LEGACY_ENTITIES.get(key)
            if not entity or not self.hass.states.get(entity):
                continue
            if domain == "input_boolean":
                service = "turn_on" if value else "turn_off"
                data = {"entity_id": entity}
            else:
                if not value:
                    continue
                service = "set_value"
                data = {"entity_id": entity, "value": str(value)[:250]}
            try:
                await self.hass.services.async_call(domain, service, data, blocking=False)
            except Exception:
                pass
