"""小峰门锁集成常量。"""
DOMAIN = "xf_lock"

CONF_UUID = "uuid"
CONF_APP_KEY = "app_key"
CONF_APP_SECRET = "app_secret"
CONF_MOVE_CARD = "move_card"
CONF_SN = "sn"
CONF_ENDPOINT = "endpoint"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_ENDPOINT = "api-cn.jftechws.com"
DEFAULT_SCAN_INTERVAL = 60

# 兼容现有 helper 实体(若存在则同步写入，保证 3D 页面/自动化无需改动)
LEGACY_ENTITIES = {
    "locked": "input_boolean.xiao_feng_men_suo_yi_shang_suo",
    "online": "input_boolean.xiao_feng_men_suo_zai_xian",
    "alarm": "input_boolean.xiao_feng_men_suo_gao_jing",
    "event": "input_text.xiao_feng_men_suo_zui_jin_shi_jian",
    "unlock": "input_text.xiao_feng_men_suo_kai_suo_fang_shi",
    "snapshot": "input_text.xiao_feng_men_suo_zhua_pai_tu_url",
}
