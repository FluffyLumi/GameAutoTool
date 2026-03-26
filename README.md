# GameAutoTool

一款专为 Windows 游戏（洛克王国等）设计的图形化自动化工具，支持鼠标键盘脚本、图像识别触发、宏录制、全局热键和定时计划任务。

---

## 功能概览

| 功能 | 说明 |
|------|------|
| 🖱 鼠标/键盘脚本 | 可视化编辑动作序列，支持点击、按键、延时等 |
| 📸 图像识别 | OpenCV 模板匹配；等待图像出现 / 条件分支执行 |
| 🔴 宏录制 | 实时录制鼠标点击和键盘操作，一键导入动作列表 |
| ⌨️ 全局热键 | F8 启动 · F9 停止 · F10 录制切换（无需聚焦窗口） |
| ⏱ 定时计划 | 支持 `HH:MM`、`30s`、`5m`、`2h` 等多种时间格式 |
| 🌿 条件分支 | `if_image_exist` / `if_image_not_exist` 子动作块 |

---

## 环境要求

- **操作系统**：Windows 10 / 11（pywin32 & DPI 感知仅 Windows 有效）
- **Python**：≥ 3.12
- **依赖库**：见 [pyproject.toml](pyproject.toml)

---

## 安装

### 方式一：uv（推荐）

```bash
# 安装 uv（若未安装）
pip install uv

# 克隆项目
git clone <repo-url>
cd GameAutoTool

# 创建虚拟环境并同步依赖
uv sync
```

### 方式二：pip

```bash
git clone <repo-url>
cd GameAutoTool
pip install -e .
```

---

## 快速开始

```bash
# uv 方式
uv run python app.py

# 或直接
python app.py
```

启动后：

1. 顶栏点击 **查找游戏窗口** → 勾选目标窗口 → **确认**
2. 左侧面板点击 **➕ 添加动作** 编辑动作列表
3. 设置循环次数（0 = 无限循环）
4. 点击 **▶ 运行** 或按 **F8** 启动执行

---

## 目录结构

```
GameAutoTool/
├── app.py                  # GUI 主入口
├── position_tool.py        # 坐标查看辅助工具
├── pyproject.toml
├── README.md
├── icon.png                # 应用图标
├── templates/              # 模板图片存储目录（自动创建）
├── actions/
│   ├── Move.py             # 动作执行引擎
│   ├── WindowsManager.py   # Win32 窗口管理
│   ├── ImageMatcher.py     # OpenCV 图像识别
│   ├── HotkeyManager.py    # 全局热键（pynput）
│   ├── MacroRecorder.py    # 宏录制（pynput）
│   └── Scheduler.py        # 定时计划（schedule）
└── utils/
    ├── ReadConfig.py       # JSON 配置读写
    └── actions_template.json
```

---

## 动作 JSON 格式参考

动作列表可通过 UI 编辑，也可直接编辑 JSON 文件（**文件 → 另存为**）。

### 1. 鼠标点击 `mouse`

```json
{
  "type": "mouse",
  "action": "click",
  "x": 320,
  "y": 240,
  "button": "left",
  "clicks": 1,
  "interval": 0.1
}
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `x`, `y` | int | 0 | 相对于游戏窗口左上角的坐标 |
| `button` | str | `"left"` | `"left"` / `"right"` / `"middle"` |
| `clicks` | int | 1 | 点击次数（2 = 双击） |
| `interval` | float | 0.1 | 多次点击间隔（秒） |

### 2. 键盘按键 `keyboard`

```json
{ "type": "keyboard", "action": "tap",    "key": "f" }
{ "type": "keyboard", "action": "press",  "key": "w", "duration": 2.0 }
{ "type": "keyboard", "action": "hotkey", "keys": ["ctrl", "c"] }
```

| `action` | 说明 |
|----------|------|
| `tap` | 短按一下（press + release） |
| `press` | 长按 `duration` 秒 |
| `hotkey` | 组合键，`keys` 为按键列表 |

### 3. 延时 `delay`

```json
{ "type": "delay", "time": 1.5 }
```

### 4. 等待图像出现 `wait_image`

```json
{
  "type": "wait_image",
  "template": "battle_ready.png",
  "confidence": 0.85,
  "timeout": 30,
  "interval": 0.5,
  "region": [0, 0, 800, 600]
}
```

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `template` | str | — | 模板文件名（位于 `templates/` 目录） |
| `confidence` | float | 0.8 | 匹配置信度阈值（0~1） |
| `timeout` | float | 30 | 最长等待秒数，超时后继续执行 |
| `interval` | float | 0.5 | 每次检测间隔（秒） |
| `region` | [x,y,w,h] | null | 限定截图区域（绝对坐标），null 表示全屏 |

### 5. 图像存在时执行 `if_image_exist`

```json
{
  "type": "if_image_exist",
  "template": "enemy.png",
  "confidence": 0.8,
  "region": null,
  "actions": [
    { "type": "mouse", "action": "click", "x": 100, "y": 200 }
  ]
}
```

当屏幕上**找到**模板图像时，执行 `actions` 子列表；否则跳过。

### 6. 图像不存在时执行 `if_image_not_exist`

```json
{
  "type": "if_image_not_exist",
  "template": "loading.png",
  "confidence": 0.8,
  "region": null,
  "actions": [
    { "type": "keyboard", "action": "tap", "key": "enter" }
  ]
}
```

当屏幕上**找不到**模板图像时，执行 `actions` 子列表。

---

## 全局热键

| 热键 | 功能 |
|------|------|
| **F8** | 启动执行当前动作列表 |
| **F9** | 停止执行 |
| **F10** | 切换宏录制（开始 / 停止） |

> **注意**：热键使用 pynput 实现，在 macOS 上需要授予辅助功能权限；在某些系统上可能需要以管理员权限运行。

---

## 图像识别工作流

1. 打开右侧 **📸 图像识别** 标签页
2. 填写模板文件名（如 `battle_btn.png`）和截图区域坐标
3. 点击 **截取模板**（3 秒倒计时，期间切换到游戏窗口截取目标区域）
4. 模板保存到 `templates/` 目录后，点击 **测试检测** 验证识别效果
5. 在动作列表中添加 `wait_image` 或 `if_image_exist` 动作并填写模板名称

---

## 宏录制工作流

1. 先在顶栏连接游戏窗口（确保坐标转换正确）
2. 打开右侧 **🔴 宏录制** 标签页，点击 **⏺ 开始录制**（或按 F10）
3. 在游戏中进行实际操作（点击、按键等）
4. 点击 **⏹ 停止录制**（或再按 F10）
5. 预览区域会显示录制的动作，确认无误后点击 **导入到动作列表**
6. 可继续在动作列表中编辑、调序、保存

> 录制时会自动插入 `delay` 动作以保留操作间的时间间隔；F8/F9/F10 热键本身不会被录制。

---

## 定时计划时间格式

| 格式 | 示例 | 说明 |
|------|------|------|
| `HH:MM` | `08:30` | 每天固定时刻执行 |
| `Xs` | `30s` | 每隔 N 秒执行 |
| `Xm` | `5m` | 每隔 N 分钟执行 |
| `Xh` | `2h` | 每隔 N 小时执行 |

定时任务执行的是**添加任务时**的动作列表快照；修改动作列表后需重新添加任务。

---

## 坐标辅助工具

```bash
python position_tool.py
```

启动后会自动前置游戏窗口，在终端实时输出当前鼠标位置的**相对坐标**（相对于游戏窗口左上角）和绝对坐标，方便填写动作 JSON 中的 `x`、`y` 字段。

---

## 常见问题

**Q: 运行时提示缺少 `win32gui`**  
A: 确保在 Windows 上运行，并已安装 `pywin32`：`pip install pywin32`

**Q: 热键无响应**  
A: 尝试以管理员权限运行；macOS 需在"系统设置 → 隐私与安全性 → 辅助功能"中授权终端或 Python。

**Q: 图像匹配总是失败**  
A: 降低置信度阈值（如从 0.8 降到 0.7）；确保截取模板时游戏分辨率与实际运行分辨率一致。

**Q: 坐标偏移不正确**  
A: 请先在顶栏查找并确认游戏窗口，确保窗口未被最大化拉伸到非标准尺寸。

---

## 依赖列表

```
customtkinter  >=5.2.0    # 深色主题 GUI
opencv-python  >=4.13.0   # 图像模板匹配
pyautogui      >=0.9.54   # 鼠标键盘控制 / 截图
pynput         >=1.7.7    # 全局热键 / 宏录制
pywin32        >=311      # Windows 窗口管理
schedule       >=1.2.0    # 定时计划
```

---

## 版本历史

| 版本 | 更新内容 |
|------|----------|
| 0.2.0 | 新增图像识别、宏录制、全局热键、定时计划、条件分支；重构 UI 至 6 标签页 |
| 0.1.0 | 基础鼠标/键盘动作执行；customtkinter UI；窗口管理 |

---

## License

MIT
