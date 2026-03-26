"""图像识别模块 - 基于 OpenCV 模板匹配"""

import os
from typing import Optional

import cv2
import numpy as np
import pyautogui


def _get_templates_dir() -> str:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    d = os.path.join(project_root, "templates")
    os.makedirs(d, exist_ok=True)
    return d


TEMPLATES_DIR: str = _get_templates_dir()


def capture_region(region: list | None = None) -> np.ndarray:
    """截取屏幕区域，region=[x, y, w, h] 或 None 截全屏，返回 BGR ndarray"""
    if region and len(region) == 4:
        x, y, w, h = region
        shot = pyautogui.screenshot(region=(x, y, w, h))
    else:
        shot = pyautogui.screenshot()
    return cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR)


def find_on_screen(
    template_name: str,
    region: list | None = None,
    confidence: float = 0.8,
) -> Optional[tuple[int, int, float]]:
    """
    在屏幕（或指定区域）查找模板图像。

    Returns:
        (abs_x, abs_y, score)  若找到，坐标为模板中心的绝对屏幕坐标
        None                   若未找到或置信度不足
    """
    template_path = os.path.join(TEMPLATES_DIR, template_name)
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"模板文件不存在: {template_path}")

    template = cv2.imread(template_path)
    if template is None:
        raise ValueError(f"无法读取模板: {template_path}")

    screenshot = capture_region(region)

    gray_ss = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
    gray_tp = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)

    result = cv2.matchTemplate(gray_ss, gray_tp, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= confidence:
        th, tw = gray_tp.shape[:2]
        cx = max_loc[0] + tw // 2
        cy = max_loc[1] + th // 2
        if region and len(region) == 4:
            cx += region[0]
            cy += region[1]
        return (cx, cy, float(max_val))
    return None


def save_template(region: list, filename: str) -> str:
    """截取屏幕区域并保存为模板文件，返回保存的绝对路径"""
    img = capture_region(region)
    if not filename.lower().endswith((".png", ".jpg", ".bmp")):
        filename += ".png"
    path = os.path.join(TEMPLATES_DIR, filename)
    cv2.imwrite(path, img)
    return path


def list_templates() -> list[str]:
    """列出 templates/ 目录下所有图像文件名"""
    return sorted(
        f
        for f in os.listdir(TEMPLATES_DIR)
        if f.lower().endswith((".png", ".jpg", ".bmp"))
    )
