# 场景 flow DSL 参考（ECA 类型表）

来源：智慧生活 App 17.0.4.312 静态反编译（classes23/24.dex）+ 账号真实场景回读。
**[实测]** = 真实场景验证；**[静态]** = 仅见于 App，参数未实测，首次使用建议先在 App 建同类节点再 detail 回读。

## flow 结构

```jsonc
{
  "type": "manual | auto | mixed",   // 服务参数 type: 1=手动 3=自动 0=混合
  "trigger": {
    "eventLogic": "any",             // any=任一事件触发；all [静态]
    "events": [ /* ScenarioTriggerEvent */ ],
    "conditions": [ /* 全局 ScenarioTriggerCondition */ ]
  },
  "actions": [ /* ScenarioAction，可嵌套 */ ],
  "version": "0.0.1"
}
```

- 事件可内嵌自己的 `conditions[]`（如给设备事件加时间段限制）
- 动作支持 `actions[]` 子动作组合、`thenActions[]`/`elseActions[]`/`express` 条件分支 [静态]、
  `delay: {delayType, time, delaySync}` 延迟

公共包裹：每个节点带 `id`（uuid4）、`enabled`、`version: "$latest"`；
参数统一放在 `params`/`input` 里，值用 `{"modify": "custom", "defaultValue": ...}` 双层包裹。

## 触发事件 eventType

| 类型 | 含义 | 状态 |
| --- | --- | --- |
| `huawei.events.manualEvent` | 手动点击卡片 | 实测 |
| `huawei.event.time` / `huawei.events.timeEvent` | 定时（含节假日、日出日落偏移 supportHoliday） | 静态 |
| `huawei.event.sunset` | 日出/日落 | 静态 |
| `events.huawei.hivoice.voiceControl` | 语音指令（params.voiceCommands.defaultValue） | 实测 |
| `hmosEca` | 鸿蒙生态事件容器（门锁门铃/蓝牙/位置等，细节云端下发） | 实测 |
| `huawei.event.OuterAntiLock` | 门锁离家/反锁模式 | 实测 |
| `events.huawei.iot.userOpenDoor` / `closeDoorOnReturn` | 开门 / 回家关门 | 静态 |
| `events.huawei.hilink.nfcTouchEvent` | NFC 标签触碰 | 静态 |
| `events.huawei.device.locationEnterEvent` / `locationExitEvent` | 进/出地理围栏（params.location.defaultValue.lat/lon/radius） | 实测 |
| `events.huawei.device.appOpenEvent` / `appCloseEvent` | App 打开/关闭 | 静态 |
| `events.huawei.ca.*` | 手机/穿戴：bluetoothDeviceConnected/Disconnected、wifiConnected/Disconnected、earphoneWear、wearStatusWear/Off、heartRate、powerStatus、sleepStatusSleep/Sleepless、appUsageDuration(Today)、phoneCallIncoming/Outgoing/HangUp/RingByName | 静态 |
| `events.huawei.hiscenario.turnOnAutoScene` | 自动场景被开启 | 静态 |

设备自身事件（传感器/按键）为云端按设备下发，本地无全集——用 detail 借同类设备场景的 flow。

## 条件 conditionType

| 类型 | 含义 | 状态 |
| --- | --- | --- |
| `huawei.condition.timeRange` | 时间段 | 实测（模板见下） |
| `huawei.condition.multiTimeRange` | 多时间段（supportHoliday） | 静态 |
| `huawei.condition.multiCountTimeRange` | 计数时间段（次数/周期 supportHoliday.period） | 静态 |
| `conditions.huawei.weather` / `weatherStatus` / `huawei.system.condition.weather.status` | 天气 | 静态 |
| `conditions.huawei.countrange` | 数值范围（设备属性阈值） | 静态 |
| `conditions.huawei.device.LocationInRange` / `LocationOutRange` | 位置在/离范围 | 静态 |
| `conditions.huawei.device.appStatusForeground` / `appStatusBackground` | App 前后台 | 静态 |
| `conditions.huawei.device.bluetoothConnected` / `wifiConnected` | 蓝牙/WiFi 已连接 | 静态 |
| `conditions.huawei.wifi.bluetoothConnected` / `bluetoothDisConnected` / `conditions.huawei.wlan.wifiDisConnected` | 蓝牙/WiFi 连接态 | 静态 |
| `conditions.huawei.device.scenarioExecuted/Executing/UnExecuted/UnExecuting` | 场景执行状态 | 静态 |
| `conditions.huawei.ca` | 手机/穿戴状态条件 | 静态 |

## 动作 actionType

**云控设备**

| 类型 | 含义 | 状态 |
| --- | --- | --- |
| `actions.huawei.cloud.onOff` | 开关 commandParams `{on: 0/1}` | 实测 |
| `actions.huawei.cloud.switchCruise` | 摄像头全景巡航 | 实测 |
| `actions.huawei.cloud.switchPhoto` | 摄像头拍照 | 实测 |
| `actions.huawei.cloud.{capabilityId}` | 其余设备能力动态拼接（brightness/colorTemperature 等），需借模板 | 云端下发 |
| `custom.action.controlDevice` / `huawei.action.onOff` | 通用设备控制 / 旧版开关 | 静态 |

**通知与手机**

- `actions.huawei.cloud.pushNotice`（推送，实测）、`playAlarm`（告警）、
  `actions.huawei.device.ttsSpeakV1`、`custom.action.randomNotificationTtsSpeakAction`（随机播报，实测）、
  `custom.action.randomNotificationPushNoticeAction`
- `actions.huawei.device.*`：vibrate（实测）、setNfc、setWlan、setBluetooth、connectBluetooth、deeplink、
  openBrowser、pauseMusic、playMusicDefault、playMusicAndLight、playRecord、callHiVoice（实测）、
  callVAssistantOpenApp（实测）、queryWeather、startNavigation、speakNavigation

**场景与系统**

- 执行其他场景：`executeScenario` / `executeScenarioEx` / `executeScenarioExV2`、`stopScenario(V2)`、
  `executeButtonScenario`、`enableScenarioV2`；进行中确认 `actions.huawei.hiscenario.ongoingConfirm(.cancel)`
- 小艺 `actions.huawei.vassistant.*`：setAlarm(AfterTime)、cancelAlarm、countDownClock、
  makePhoneCall、makeMeetimePhoneCall/VideoCall、makeWeChatVoiceCall/VideoCall、
  sendWeChatMessage/Location、navigateBdMap/navigateGdMap、viewBdMapRoute/viewGdMapRoute
- 其他：`actions.huawei.app.shortcuts`、`actions.huawei.app.petaltravels`、
  `custom.action.speakSchedule`、`custom.action.speakWeather`、`custom.action.music`、
  `actions.huawei.hiscenario.operateSpaceTheme`

## 模板：时间段条件（挂事件的 conditions 内）[实测]

```json
{
  "conditionId": "<uuid4>",
  "conditionType": "huawei.condition.timeRange",
  "conditionUiid": "ui.huawei.selectNormalizedTimeRange:type(timeRange)",
  "params": {
    "startTime": {"modify": "custom", "defaultValue": "8H0", "defaultValue~": {"hour": 8, "minute": 0, "type": "timePicker"}},
    "endTime":   {"modify": "custom", "defaultValue": "18H0", "defaultValue~": {"hour": 18, "minute": 0, "type": "timePicker"}},
    "day": {"modify": "custom", "defaultValue": "", "defaultValue~": "everyday"},
    "type": {"modify": "custom", "defaultValue": "event"},
    "skipHoliday": {"modify": "skip", "defaultValue": false},
    "maxCount": {"modify": "custom", "defaultValue": -1, "defaultValue~": "NoLimit"},
    "timeUnit": {"modify": "custom", "defaultValue": "hour"},
    "timeInterval": {"modify": "custom", "defaultValue": 0},
    "dayOfWeek": {"modify": "custom", "defaultValue": ""},
    "month": {"modify": "custom", "defaultValue": ""},
    "year": {"modify": "custom", "defaultValue": ""}
  },
  "version": "$latest", "enabled": true, "conditionFlag": 0
}
```

时间字符串格式 `"8H0"` = 8:00；星期走 day/dayOfWeek（everyday/工作日/自定义）。

## 模板：设备开关动作 [实测]

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

组合动作：外层 `custom.action.switchCruise` 等的 `actions[]` 里放多个上述云控动作（巡航=onOff+switchCruise+switchPhoto）。

## 注意

- 空 actions 创建被拒 errcode 3008；手动场景 type=1 不允许 set_enabled（云端拒绝）。
- 场景执行日志不记录手动执行结果，验证 run 以响应 `code:0` 为准。
- [静态] 类型首次使用务必 App 建一次再 detail 回读，避免参数包裹结构偏差。
