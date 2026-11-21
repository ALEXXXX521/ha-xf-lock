"""小峰门锁配置向导。"""
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import fetch_all
from .const import (
    DOMAIN, CONF_UUID, CONF_APP_KEY, CONF_APP_SECRET, CONF_MOVE_CARD,
    CONF_SN, CONF_ENDPOINT, CONF_SCAN_INTERVAL,
    DEFAULT_ENDPOINT, DEFAULT_SCAN_INTERVAL,
)


def _cfg_from_data(data):
    return {
        "uuid": data[CONF_UUID],
        "app_key": data[CONF_APP_KEY],
        "app_secret": data[CONF_APP_SECRET],
        "move_card": int(data[CONF_MOVE_CARD]),
        "sn": data[CONF_SN],
        "endpoint": data.get(CONF_ENDPOINT, DEFAULT_ENDPOINT),
    }


class XFLockConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            cfg = _cfg_from_data(user_input)
            # 用 HA 的执行器跑阻塞的 urllib 调用，避免阻塞事件循环
            try:
                await self.hass.async_add_executor_job(fetch_all, cfg)
            except Exception:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(cfg["sn"])
                self._abort_if_unique_id_configured()
                title = "小峰门锁 " + cfg["sn"][-4:]
                return self.async_create_entry(title=title, data=user_input)

        schema = vol.Schema({
            vol.Required(CONF_UUID): str,
            vol.Required(CONF_APP_KEY): str,
            vol.Required(CONF_APP_SECRET): str,
            vol.Required(CONF_MOVE_CARD, default=2): vol.In([1, 2, 3, 4]),
            vol.Required(CONF_SN): str,
            vol.Optional(CONF_ENDPOINT, default=DEFAULT_ENDPOINT): str,
            vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
                vol.Coerce(int), vol.Range(min=10, max=3600)
            ),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return XFLockOptionsFlow(config_entry)


class XFLockOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, entry):
        self._entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        cur = self._entry.options.get(CONF_SCAN_INTERVAL,
                                      self._entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        return self.async_show_form(step_id="init", data_schema=vol.Schema({
            vol.Optional(CONF_SCAN_INTERVAL, default=cur): vol.All(
                vol.Coerce(int), vol.Range(min=10, max=3600)
            ),
        }))
