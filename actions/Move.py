import time
import pyautogui as pa

# Safe
pa.FAILSAFE = True
pa.PAUSE = 0.05

def execuate_actions(actions):
    for act in actions:
        try:
            if act["type"] == "mouse":
                handle_mouse(act)
            elif act["type"] == "keyboard":
                handle_keyboard(act)
            elif act["type"] == "delay":
                time.sleep(act["time"])
        except Exception as e:
            print(f"执行出错: {e}")

# Mouse control
def handle_mouse(act, win_left, win_top):
    action = act["action"]

    if action == "click":
        pa.click(x=act.get("x", None)+win_left, y=act.get("y", None)+win_top, button=act.get("button", "left"), clicks=act.get("clicks", 1), interval=act.get("interval", 0.1))

def handle_keyboard(act):
    action = act["action"]

    if action == "tap":
        pa.press(act["key"])
    elif action == "press":
        key = act["key"]
        duration = act.get("duration", 0.1)

        pa.keyDown(key=key)
        time.sleep(duration)
        pa.keyUp(key=key)

    elif action == "hotkey":
        pa.hotkey(*act["keys"])