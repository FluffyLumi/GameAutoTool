import pyautogui as pa

# 用position_tool获取相对位置，这里输入窗口左上角坐标
def Click_Close(win_left, win_top):
    close_x = 1845
    close_y = 95
    real_x = close_x + win_left
    real_y = close_y + win_top
    pa.click(x=real_x, y=real_y, button='left')