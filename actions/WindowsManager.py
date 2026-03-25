import win32gui
import win32con
import time

class WindowsManager:
    def __init__(self):
        self.hwnd = None
        self.window_name = None
        self.class_name = None
        self.left = None
        self.top = None
        self.right = None
        self.bottom = None
        self.width = None
        self.height = None

    def find_window(self, WindowName, ClassName):
        if ClassName:
            self.hwnd = win32gui.FindWindow(ClassName, WindowName)
        else:
            self.hwnd = win32gui.FindWindow(None, WindowName)

        if not self.hwnd:
            return False
        else:
            self.window_name = win32gui.GetWindowText(self.hwnd)
            self.class_name = win32gui.GetClassName(self.hwnd)

            self.left, self.top, self.right, self.bottom = win32gui.GetWindowRect(self.hwnd)
            self.width = self.right - self.left
            self.height = self.bottom - self.top
        return True

    def bring_to_foreground(self):
        try:
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            time.sleep(0.5)
            win32gui.SetForegroundWindow(self.hwnd)
            time.sleep(0.5)
            return True
        except Exception as e:
            print(f"设置前台窗口失败: {e}")
            return False

    def hide_window(self):
        """隐藏窗口"""
        if self.hwnd:
            win32gui.ShowWindow(self.hwnd, win32con.SW_HIDE)