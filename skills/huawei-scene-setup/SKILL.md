---
name: huawei-scene-setup
description: 通过 Home Assistant 的 huawei_smarthome_plus 集成创建和管理华为智慧生活场景与自动化。当用户要求创建/修改/删除智慧生活场景、设置定时或设备联动自动化、生成场景 flow、查阅场景 ECA 类型（触发/条件/动作）时使用。不用于房间管理、设备改名/转移/解绑等非场景操作。
---

# 华为智慧生活场景设置

通过 HA 上已安装的 `huawei_smarthome_plus` 集成（20 个服务，凭证借用原集成
`huawei_smarthome`，无需账号密码），完成场景的查询、创建、修改、执行、删除。
前置条件：HA 已安装并配置好上述两个集成（GitHub: C3H3-AI/ha-huawei-smarthome-plus）。

## 环境约定

- HA 地址默认 `http://localhost:8123`，远程 HA 用 `--base` 或环境变量 `HA_BASE` 指定
- 令牌使用 HA「个人资料」页底部生成的**长期访问令牌**（Long-Lived Access Token）；
  解析顺序 `--token` > 环境变量 `HA_TOKEN` > 令牌文件 `~/.ha_long_lived_token`
- 脚本启动时会逐个候选令牌请求 `/api/` 实测认证，失效的自动跳过
  （stderr 的 `[warn] 失效令牌来源…` 属正常，常见于环境里残留过期的 HA_TOKEN）
- 仅依赖 Python requests，遵循系统代理设置
- 所有调用走 HA 服务接口 `/api/services/huawei_smarthome_plus/<svc>?return_response`
- 详细 ECA 类型与模板见 `references/scene-flow.md`；精确 HTTP 调用一律走脚本，不要手写请求

## 标准工作流（创建场景必须按此顺序）

1. **摸底**：`scenes` 看现有场景；`devices` / `rooms` 拿目标设备 `dev_id` 和房间 `room_id`。
2. **借模板**：优先找一个触发/动作最接近的已有场景，`detail <scenario_id>` 拿完整 flow 复制。
   不要凭空拼 DSL——设备能力类型（`actions.huawei.cloud.{capabilityId}`）由云端按设备下发，
   猜出来的 capabilityId 大概率无效。
3. **改参数**：只替换设备 id、`commandParams`、时间、标题；保留 `version:"$latest"`、
   `modify:"custom"/"fix"`、UUID 全部重新生成。
4. **创建**：把 flow 存成 JSON 文件，用 `create --flow @flow.json`。
   注意：无任何动作的空 flow 会被云端拒绝（errcode 3008），必须含至少一个动作。
5. **验证**：创建成功后 `detail` 回读，并在智慧生活 App 确认卡片显示正常；需要时 `run <id>` 试执行。
6. **清理**：验收/测试场景用完即 `delete <id>`，不要在用户账号留垃圾场景。

## 脚本用法

脚本路径 `scripts/huawei_scene.py`（Python，仅依赖 requests）。

```bash
# 查询类
python huawei_scene.py scenes                     # 列场景（id/标题/类型/启用）
python huawei_scene.py detail <scenario_id>       # 完整 flow（创建模板来源）
python huawei_scene.py devices [--keyword 灯带]   # 设备清单（dev_id/型号/房间）
python huawei_scene.py rooms                      # 房间清单（room_id/楼层/设备数）
python huawei_scene.py logs [--page-size 20]      # 执行日志

# 写操作（危险动作脚本会先打印 payload 并要求 --yes）
python huawei_scene.py create --title "夜灯" --flow @flow.json [--type 1|3|0] [--home-id HID]
python huawei_scene.py update <id> --flow @flow.json [--title T] [--enabled true|false]
python huawei_scene.py run <id>                  # 立即执行
python huawei_scene.py enable <id> --off         # 启用/禁用（手动场景 type=1 云端不支持禁用）
python huawei_scene.py rename <id> --title "新名"
python huawei_scene.py move <id> --room-id RID [--home-id HID]
python huawei_scene.py delete <id> --yes
```

HA 地址与 token 可用 `--base`、`--token` 或环境变量 `HA_BASE` / `HA_TOKEN` 覆盖；
flow 入参既可以是内联 JSON 字符串，也可以是 `@文件路径`。

## flow 最小骨架

完整字段与类型表见 `references/scene-flow.md`。手动场景（type=1）只需：

```json
{
  "type": "manual",
  "trigger": {"events": [{"eventId": "<uuid4>", "eventType": "huawei.events.manualEvent",
                          "title": "点击此场景卡片", "version": "$latest", "enabled": true}]},
  "actions": [],
  "version": "0.0.1"
}
```

设备开关动作（actions 数组元素，设备 id 来自 `devices` 命令）：

```json
{
  "actionId": "<uuid4>",
  "actionType": "actions.huawei.cloud.onOff",
  "input": [
    {"modify": "custom", "targetEntity": {"destDeviceId": "<dev_id>", "capabilityId": "onOff"}},
    {"modify": "fix", "commandParams": {"on": 1}}
  ],
  "output": {}, "version": "$latest", "enabled": true
}
```

## 红线

- 删除/执行/禁用类操作先向用户确认（脚本有 `--yes` 闸门，不要自动带）。
- 不提交任何含真实 token / 家庭 id / 设备 id 的文件到 git。
- 场景里引用的设备必须真实存在；创建后核对 App，失败的场景立即删除。
