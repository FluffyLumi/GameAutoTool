import win32gui
import win32con
import win32com.client
import pyautogui
import time

def main(WindowName, ClassName):
    '''抓取窗口'''
    hwnd = win32gui.FindWindow(ClassName, WindowName)
    # window_text = win32gui.GetWindowText(hwnd)
    # class_name = win32gui.GetClassName(hwnd)
    # print(f"窗口名称：{window_text}，窗口类型：{class_name}")
    if hwnd:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        # shell = win32com.client.Dispatch("WScript.Shell")
        # shell.SendKeys('%')  # 模拟按下 Alt
        win32gui.SetForegroundWindow(hwnd)
        # 行为代码
        # pyautogui.keyDown('w')
        # time.sleep(3)
        # pyautogui.keyUp('W')
    else:
        print("没找到窗口")


if __name__ == "__main__":
    main("test.txt - Notepad", "Notepad")
