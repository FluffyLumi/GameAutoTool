import pyautogui
import time
from actions.WindowsManager import WindowsManager


def track_mouse_position(WindowName) -> bool:
    """实时追踪鼠标相对于目标窗口的坐标，按 Ctrl+C 停止"""
    wm = WindowsManager()
    if not wm.find_window(WindowName, None):
        print(f"未找到该窗口！")
        return False

    # bring_to_foreground 才会填充 left/top
    wm.bring_to_foreground()
    win_left = wm.left
    win_top = wm.top

    print("开始追踪鼠标位置，按 Ctrl+C 停止...")
    try:
        while True:
            x, y = pyautogui.position()
            rel_x = x - win_left
            rel_y = y - win_top
            print(
                f"相对坐标: ({rel_x:4d}, {rel_y:4d})  绝对坐标: ({x:4d}, {y:4d})    ",
                end="\r",
            )
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n追踪已停止")
    return True


if __name__ == "__main__":
    # 使用方法：传入目标窗口标题
    track_mouse_position("QQ")
