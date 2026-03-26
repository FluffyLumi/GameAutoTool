from actions.WindowsManager import WindowsManager
import actions.Move as move
import utils.ReadConfig as ReadConfig

def main():
    pass

if __name__ == "__main__":
    wm = WindowsManager()

    # UnrealWindow
    if not wm.find_window("洛克王国：世界  ", "UnrealWindow"):
        print(f"未找到该窗口！")
    else:
        wm.bring_to_foreground()
        print(f"Window Name: {wm.window_name}, Class Name: {wm.class_name}")
        print(f"1: {wm.left} \n 2. {wm.top}")
        actions = ReadConfig.load_actions()
        # move.handle_mouse(actions[0], wm.left, wm.top)
        move.handle_keyboard(actions[1])