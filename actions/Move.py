import time
from typing import Callable, Optional

import pyautogui as pa

# Safe
pa.FAILSAFE = True
pa.PAUSE = 0.05


def execute_actions(
    actions: list,
    win_left: int = 0,
    win_top: int = 0,
    log_fn: Optional[Callable[[str], None]] = None,
    stop_check: Optional[Callable[[], bool]] = None,
):
    """
    执行动作序列。

    Args:
        actions:    动作列表
        win_left:   目标窗口左边界绝对坐标
        win_top:    目标窗口上边界绝对坐标
        log_fn:     日志回调 log_fn(msg)
        stop_check: 中止检测回调，返回 True 时立即中止
    """

    def _log(msg: str):
        if log_fn:
            log_fn(msg)

    def _stopped() -> bool:
        return bool(stop_check()) if stop_check else False

    for act in actions:
        if _stopped():
            break
        t = act.get("type")
        try:
            if t == "mouse":
                handle_mouse(act, win_left, win_top)
            elif t == "keyboard":
                handle_keyboard(act)
            elif t == "delay":
                time.sleep(act["time"])
            elif t == "wait_image":
                _exec_wait_image(act, _log, _stopped)
            elif t in ("if_image_exist", "if_image_not_exist"):
                _exec_if_image(act, win_left, win_top, _log, _stopped)
            else:
                _log(f"未知动作类型: {t!r}")
        except Exception as e:
            _log(f"执行出错 [{t}]: {e}")


# ── 鼠标 ──────────────────────────────────────────────────────


def handle_mouse(act: dict, win_left: int, win_top: int):
    action = act["action"]
    if action == "click":
        pa.click(
            x=act.get("x", 0) + win_left,
            y=act.get("y", 0) + win_top,
            button=act.get("button", "left"),
            clicks=act.get("clicks", 1),
            interval=act.get("interval", 0.1),
        )


# ── 键盘 ──────────────────────────────────────────────────────


def handle_keyboard(act: dict):
    action = act["action"]
    if action == "tap":
        pa.press(act["key"])
    elif action == "press":
        pa.keyDown(act["key"])
        time.sleep(act.get("duration", 0.1))
        pa.keyUp(act["key"])
    elif action == "hotkey":
        pa.hotkey(*act["keys"])


# ── 图像动作（懒加载 cv2/pyautogui，避免无关环境报错）─────────────


def _exec_wait_image(
    act: dict,
    log_fn: Callable[[str], None],
    stopped: Callable[[], bool],
):
    """等待指定模板图像出现，超时则继续执行后续动作"""
    from actions.ImageMatcher import find_on_screen

    template = act["template"]
    region = act.get("region")  # [x, y, w, h] 或 None
    confidence = act.get("confidence", 0.8)
    timeout = act.get("timeout", 30)
    interval = act.get("interval", 0.5)

    log_fn(f"  ⏳ 等待 {template}（最长 {timeout}s，置信度 {confidence}）")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if stopped():
            return
        result = find_on_screen(template, region, confidence)
        if result:
            log_fn(f"  ✅ 找到 {template}  置信度 {result[2]:.2f}")
            return
        time.sleep(interval)
    log_fn(f"  ⚠ 等待 {template} 超时，继续执行")


def _exec_if_image(
    act: dict,
    win_left: int,
    win_top: int,
    log_fn: Callable[[str], None],
    stopped: Callable[[], bool],
):
    """条件分支：图像存在/不存在时执行对应的子动作列表"""
    from actions.ImageMatcher import find_on_screen

    t = act["type"]
    template = act["template"]
    region = act.get("region")
    confidence = act.get("confidence", 0.8)

    result = find_on_screen(template, region, confidence)
    found = result is not None
    expect_found = t == "if_image_exist"
    branch = "then" if (found == expect_found) else "else"
    sub_actions = act.get(branch, [])

    cond_desc = "存在" if expect_found else "不存在"
    hit_desc = "命中" if found == expect_found else "跳过"
    log_fn(
        f"  [🔀 若{cond_desc} {template}] {hit_desc} → "
        f"执行 {branch} 分支（{len(sub_actions)} 个动作）"
    )
    if sub_actions:
        execute_actions(sub_actions, win_left, win_top, log_fn, stopped)
