# 小峰门锁集成（Home Assistant）

让 Home Assistant 直接对接杰峰（JFTECH / 小峰管家）云锁 OpenAPI，在 HA 本机完成签名、令牌刷新、状态读取和门铃抓拍——**不需要电脑桥接**。

## 功能

- 在线状态、是否上锁、告警（二进制传感器）
- 最近事件、开锁方式（文本传感器）
- 门铃抓拍图（摄像头实体 + 抓拍图 URL 传感器）
- 自动刷新 deviceToken（24 小时有效期，集成内 20 小时自动重取）
- 自动刷新抓拍图签名 URL（每次轮询重新签名，永不过期）
- 兼容旧版桥接脚本的 `input_*` helper 实体（若存在则同步写入，3D 页面/自动化无需改动）

## 前置条件

1. 门锁已绑定到杰峰开放平台应用（`https://open.jftech.com`）。
2. 已从开放平台应用详情页获取：`uuid`、`AppKey`、`AppSecret`、`moveCard`。
3. 设备完整序列号。

> 门锁是电池低功耗设备，实时视频流不可行（需物理唤醒且 3 秒内拉流）。本集成呈现的是**门铃按铃瞬间的抓拍快照**。

## 安装

### 方式一：HACS 自定义仓库（推荐）

1. 把本仓库上传为你的 GitHub 公开仓库。
2. HA → 设置 → HACS → 右上角菜单 → 自定义仓库 → 添加：
   - 链接：`https://github.com/ALEXXXX521/ha-xf-lock`
   - 类别：Integration
3. 在 HACS 里搜索「小峰门锁」，安装。
4. 重启 Home Assistant。

### 方式二：手动安装

1. 把 `custom_components/xf_lock/` 整个文件夹复制到 HA 配置目录的 `custom_components/` 下。
2. 重启 Home Assistant。

## 配置

设置 → 设备与服务 → 添加集成 → 搜索「小峰门锁」→ 填入凭证：

| 字段 | 说明 |
|------|------|
| uuid | 开放平台应用 uuid |
| AppKey | 应用 AppKey |
| AppSecret | 应用 AppSecret |
| moveCard | 应用页面显示的 moveCard（常见 1 或 2）|
| 设备完整序列号 | 门锁 SN |
| 接入点域名 | 默认 `api-cn.jftechws.com` |
| 刷新间隔 | 默认 60 秒 |

配置向导会立即调用一次 API 验证凭证；成功才保存。

## 实体

配置后自动生成：

- `binary_sensor.小峰门锁_在线 / 已上锁 / 告警`
- `sensor.小峰门锁_最近事件 / 开锁方式 / 抓拍图url`
- `camera.小峰门锁摄像头`

## 依赖

纯 Python 标准库（hashlib / urllib / json），无第三方 pip 依赖。

## 许可证

MIT
