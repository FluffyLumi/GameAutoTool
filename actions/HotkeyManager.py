"""全局热键管理 - 基于 pynput.keyboard.GlobalHotKeys"""

import threading
from typing import Callable

from pynput import keyboard


class HotkeyManager:
    """
    注册并监听全局热键，支持 <f8> / <f9> / <f10> 等功能键。
    回调在独立线程中触发，UI 更新请通过 widget.after(0, fn) 派发。
    """

    def __init__(self):
        self._hotkeys: dict[str, Callable] = {}
        self._listener: keyboard.GlobalHotKeys | None = None

    def register(self, key_name: str, callback: Callable):
        """
        key_name: pynput GlobalHotKeys 格式，如 '<f8>', '<f9>'
        callback: 触发时调用（在 pynput 线程中）
        """
        self._hotkeys[key_name] = callback

    def start(self):
        if not self._hotkeys or self._listener:
            return
        self._listener = keyboard.GlobalHotKeys(self._hotkeys)
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()
            self._listener = None
