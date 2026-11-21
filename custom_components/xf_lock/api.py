"""杰峰(小峰管家) OpenAPI 底层客户端 —— 纯标准库实现。

签名算法、device token、状态、报警解析均从已验证的 Python 桥接脚本移植。
本模块不依赖任何第三方库(hashlib/urllib/json 均为标准库)。
"""
import hashlib
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

DEFAULT_ENDPOINT = "api-cn.jftechws.com"

# ---- 事件映射(与现有桥接脚本保持一致) ----
MSG_TYPE_NAMES = {
    "FingerPrint": "指纹", "Face": "人脸", "DoorBell": "门铃",
    "Password": "密码", "Card": "刷卡", "Key": "钥匙",
    "Remote": "远程", "App": "手机", "Temp": "临时密码",
    "Voice": "语音", "Tourist": "访客", "Recognition": "人脸识别",
}
EVENT_NAMES = {
    "DoorLockCall": "门铃", "DoorBell": "门铃",
    "LowBattery": "低电量", "TamperAlarm": "防拆报警",
    "WrongPassword": "密码错误", "AntiLock": "反锁",
}
LOCK_EVENTS = {"Locked", "DoorLocked", "Lock", "AdminLock"}
UNLOCK_EVENTS = {
    "DoorLockOpen", "DoorLockUnlock", "Unlock", "DefaultUnLock",
    "EmergencyUnLock", "InDrHandleUnLock", "InDrButtonUnLock",
}
ALARM_EVENTS = {
    "LowBattery", "TamperAlarm", "WrongPassword", "DoorbellAlarm",
    "FireAlarm", "GasAlarm", "IllegalUnlock", "PrizeLock", "KeyLock",
}

_counter = 0


def _time_millis():
    global _counter
    _counter += 1
    return "%07d%d" % (_counter % 10000000, int(time.time() * 1000))


def signature(uuid_, app_key, app_secret, time_millis, move_card):
    """杰峰 OpenAPI 签名: MD5(原文 + 移位后的原文倒序)。"""
    s = uuid_ + app_key + app_secret + str(time_millis)
    orig = list(s.encode("iso-8859-1"))
    chg = list(s.encode("iso-8859-1"))
    n = len(chg)
    for i in range(n):
        tmp = chg[i] if (i % move_card) > ((n - i) % move_card) else chg[n - (i + 1)]
        chg[i] = chg[n - (i + 1)]
        chg[n - (i + 1)] = tmp
    return hashlib.md5(bytes(orig + chg[::-1])).hexdigest()


def api_post(endpoint, path, cfg, body, timeout=20):
    """带签名的 POST。返回解析后的 dict。"""
    tm = _time_millis()
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "ha-xf-lock",
        "uuid": cfg["uuid"],
        "appKey": cfg["app_key"],
        "timeMillis": tm,
        "signature": signature(
            cfg["uuid"], cfg["app_key"], cfg["app_secret"], tm,
            int(cfg.get("move_card", 2) or 2),
        ),
    }
    url = "https://" + (endpoint or DEFAULT_ENDPOINT).rstrip("/") + path
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST", headers=headers
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def get_device_token(cfg, cached_token=None, cached_saved=0.0, force=False):
    """获取 deviceToken。返回 (token, saved_timestamp)。

    缓存 20 小时(带签名有效期 24h,留 4h 余量)。集成重启后缓存丢失会自动重取。
    """
    if (not force and cached_token and time.time() - cached_saved < 20 * 3600):
        return cached_token, cached_saved
    body = {"sns": [cfg["sn"]]}
    res = api_post(cfg.get("endpoint", DEFAULT_ENDPOINT), "/gwp/v3/rtc/device/token", cfg, body)
    if res.get("code") != 2000 or not res.get("data"):
        raise RuntimeError("获取 deviceToken 失败: %s" % res)
    return res["data"][0]["token"], time.time()


def fetch_status(cfg, token):
    res = api_post(cfg.get("endpoint", DEFAULT_ENDPOINT), "/gwp/v3/rtc/device/status", cfg,
                   {"deviceTokenList": [token], "region": "Local"})
    data = res.get("data") or []
    return data[0] if data else {}


def fetch_alarms(cfg, token, hours=720):
    now = datetime.now()
    body = {
        "startTime": (now - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S"),
        "endTime": now.strftime("%Y-%m-%d %H:%M:%S"),
        "pageNum": 1, "pageSize": 100, "protocolFmt": "0",
    }
    res = api_post(
        cfg.get("endpoint", DEFAULT_ENDPOINT),
        "/gwp/v3/rtc/device/getDeviceAlarmList/" + urllib.parse.quote(token, safe=""),
        cfg, body,
    )
    return ((res.get("data") or {}).get("AlarmArray") or [])


def parse_state(alarms):
    """从报警列表解析出门锁状态字典。"""
    alarms = sorted(alarms, key=lambda x: x.get("AlarmTime", ""))
    locked = None
    last_event = ""
    last_unlock = ""
    alarm = False
    snapshot_url = ""
    snapshot_time = ""
    for a in alarms:
        ev = (a.get("AlarmEvent") or "").split(":")[0]
        tm = a.get("AlarmTime", "")
        pic = a.get("PicInfo") or {}
        pic_url = pic.get("Url", "")
        if pic_url and tm > snapshot_time:
            snapshot_time, snapshot_url = tm, pic_url
        for pi in (a.get("PicInfos") or []):
            u = pi.get("Url", "")
            if u and tm > snapshot_time:
                snapshot_time, snapshot_url = tm, u
        try:
            msg = json.loads(a.get("AlarmMsg") or "{}")
        except Exception:
            msg = {}
        msg_type = msg.get("MsgType", "")
        method = MSG_TYPE_NAMES.get(msg_type, msg_type)
        if ev in LOCK_EVENTS:
            locked = True
            last_event = "[%s] %s" % (tm, EVENT_NAMES.get(ev, ev))
        elif ev in UNLOCK_EVENTS:
            locked = False
            last_event = "[%s] %s开锁" % (tm, method) if method else "[%s] 开锁" % tm
            last_unlock = method or EVENT_NAMES.get(ev, ev)
        elif ev in ALARM_EVENTS:
            alarm = True
            last_event = "[%s] %s" % (tm, EVENT_NAMES.get(ev, ev))
        elif ev in ("DoorLockCall", "DoorBell") or msg_type == "DoorBell":
            last_event = "[%s] 门铃" % tm
    return {
        "locked": bool(locked),
        "last_event": last_event or "暂无记录",
        "last_unlock": last_unlock or "暂无记录",
        "alarm": alarm,
        "snapshot_url": snapshot_url,
    }


def fetch_all(cfg, cached_token=None, cached_saved=0.0):
    """完整刷新一次。返回 (state_dict, token, saved_timestamp)。"""
    token, saved = get_device_token(cfg, cached_token, cached_saved)
    try:
        status = fetch_status(cfg, token)
        online = status.get("status") == "online"
    except Exception:
        online = False
    alarms = fetch_alarms(cfg, token)
    state = parse_state(alarms)
    state["online"] = online
    return state, token, saved
