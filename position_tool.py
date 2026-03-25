import pyautogui
import time
from actions.WindowsManager import WindowsManager

def track_mouse_position(WindowName) -> bool:
    wm = WindowsManager()
    if not wm.find_window(WindowName, None):
        print(f"未找到该窗口！")
        return False
    else:
        win_left = wm.left
        win_top = wm.top
    """实时追踪鼠标位置，按 Ctrl+C 停止"""
    print("开始追踪鼠标位置，按 Ctrl+C 停止...")
    try:
        while True:
            x, y = pyautogui.position()
            x = x - win_left
            y = y - win_top
            # 实时显示当前位置
            print(f"鼠标坐标: ({x:4d}, {y:4d})    ", end='\r')
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n追踪已停止")
    return True

# 使用方法
track_mouse_position("QQ")