"""宏录制模块 - 基于 pynput 监听真实鼠标/键盘操作，自动转换为 JSON 动作格式"""

import threading
import time
from typing import Callable, Optional

from pynput import keyboard as _kb, mouse as _mouse


class MacroRecorder:
    """
    实时录制鼠标点击和键盘按键，转换为与 Move.py 兼容的 JSON 动作列表。

    录制逻辑：
    - 鼠标按下 (click pressed) → 记录 mouse/click 动作
    - 键盘释放 (key_release)   → 记录 keyboard/tap 动作
    - 两个动作之间的空白时间   → 自动插入 delay 动作
    - F9 / F10 等热键           → 过滤，不录入
    """

    FILTER_KEYS = {"f9", "f10", "f8"}

    def __init__(self):
        self.actions: list[dict] = []
        self.recording = False
        self.win_left = 0
        self.win_top = 0
        self._last_time: float = 0.0
        self._lock = threading.Lock()
        self._mouse_listener: Optional[_mouse.Listener] = None
        self._kb_listener: Optional[_kb.Listener] = None
        self._on_update: Optional[Callable[[list], None]] = None

    def set_window_offset(self, left: int, top: int):
        """设置游戏窗口左上角的绝对坐标，用于转换相对坐标"""
        self.win_left = left
        self.win_top = top

    def set_update_callback(self, callback: Callable[[list], None]):
        """每录入一个新动作后回调；注意回调在 pynput 线程中触发"""
        self._on_update = callback

    # ── 控制 ─────────────────────────────────────────────────

    def start(self):
        self.actions = []
        self._last_time = time.time()
        self.recording = True

        self._mouse_listener = _mouse.Listener(on_click=self._on_click)
        self._kb_listener = _kb.Listener(on_release=self._on_key_release)
        self._mouse_listener.daemon = True
        self._kb_listener.daemon = True
        self._mouse_listener.start()
        self._kb_listener.start()

    def stop(self):
        self.recording = False
        if self._mouse_listener:
            self._mouse_listener.stop()
            self._mouse_listener = None
        if self._kb_listener:
            self._kb_listener.stop()
            self._kb_listener = None

    # ── 内部 ─────────────────────────────────────────────────

    def _append(self, act: dict):
        now = time.time()
        delay = round(now - self._last_time, 3)
        with self._lock:
            if delay >= 0.05:
                self.actions.append({"type": "delay", "time": delay})
            self.actions.append(act)
            self._last_time = now
            snapshot = list(self.actions)
        if self._on_update:
            self._on_update(snapshot)

    def _on_click(self, x: int, y: int, button: _mouse.Button, pressed: bool):
        if not pressed or not self.recording:
            return
        btn_name = (
            "left"
            if button == _mouse.Button.left
            else "right" if button == _mouse.Button.right else "middle"
        )
        self._append(
            {
                "type": "mouse",
                "action": "click",
                "x": x - self.win_left,
                "y": y - self.win_top,
                "button": btn_name,
                "clicks": 1,
                "interval": 0.1,
            }
        )

    def _on_key_release(self, key):
        if not self.recording:
            return
        key_name = self._get_key_name(key)
        if key_name and key_name not in self.FILTER_KEYS:
            self._append({"type": "keyboard", "action": "tap", "key": key_name})

    @staticmethod
    def _get_key_name(key) -> Optional[str]:
        try:
            return key.char
        except AttributeError:
            return str(key).replace("Key.", "").lower()
