"""
GameAutoTool – Windows 游戏自动化工具
功能：动作序列执行 / 图像识别触发 / 全局热键 / 宏录制 / 条件分支 / 定时计划
运行：python app.py
"""

import json
import os
import threading
import time

import customtkinter as ctk
import pyautogui
import tkinter as tk
from tkinter import filedialog, messagebox

from actions.WindowsManager import WindowsManager
import actions.Move as move
from actions.ImageMatcher import (
    TEMPLATES_DIR,
    find_on_screen,
    list_templates,
    save_template,
)
from actions.MacroRecorder import MacroRecorder
from actions.HotkeyManager import HotkeyManager
from actions.Scheduler import Scheduler, ScheduledTask

# ─────────────────────────────────────────
# 全局样式
# ─────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

FONT_MONO = ("Consolas", 10)
FONT_BODY = ("Microsoft YaHei UI", 10)
FONT_BOLD = ("Microsoft YaHei UI", 11, "bold")
FONT_TITLE = ("Microsoft YaHei UI", 14, "bold")
FONT_SMALL = ("Microsoft YaHei UI", 9)

COLOR_GREEN = ("#27ae60", "#2ecc71")
COLOR_RED = ("#c0392b", "#e74c3c")
COLOR_PURPLE = ("#7d3c98", "#9b59b6")
COLOR_BLUE = ("#1a5276", "#2980b9")
COLOR_ORANGE = ("#ca6f1e", "#e67e22")
COLOR_TEAL = ("#117a65", "#1abc9c")


# ═════════════════════════════════════════
# 动作编辑对话框
# ═════════════════════════════════════════
class ActionDialog(ctk.CTkToplevel):
    """添加 / 编辑单个动作的弹窗，支持全部动作类型"""

    ALL_TYPES = [
        "mouse",
        "keyboard",
        "delay",
        "wait_image",
        "if_image_exist",
        "if_image_not_exist",
    ]

    _SIZES = {
        "mouse": "440x340",
        "keyboard": "440x310",
        "delay": "440x220",
        "wait_image": "480x370",
        "if_image_exist": "560x520",
        "if_image_not_exist": "560x520",
    }

    def __init__(self, parent, action: dict | None, callback):
        super().__init__(parent)
        self.action = dict(action) if action else {}
        self.callback = callback

        self.title("编辑动作")
        self.geometry("440x340")
        self.resizable(False, False)
        self.grab_set()
        self.lift()
        self.focus_force()

        self._build()
        if self.action:
            self._load()

    # ---------- 框架 ----------

    def _build(self):
        pad = {"padx": 14, "pady": 6}
        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="动作类型:", font=FONT_BODY).grid(
            row=0, column=0, sticky="e", **pad
        )
        self.type_var = tk.StringVar(value="mouse")
        ctk.CTkOptionMenu(
            self,
            variable=self.type_var,
            values=self.ALL_TYPES,
            font=FONT_BODY,
            command=self._on_type_change,
        ).grid(row=0, column=1, sticky="ew", **pad)

        self.dyn = ctk.CTkFrame(self, fg_color="transparent")
        self.dyn.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10)
        self.dyn.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=2, column=0, columnspan=2, pady=14)
        ctk.CTkButton(
            btn_row, text="✓  确定", width=110, font=FONT_BODY, command=self._save
        ).pack(side="left", padx=8)
        ctk.CTkButton(
            btn_row,
            text="✕  取消",
            width=110,
            font=FONT_BODY,
            fg_color="gray40",
            hover_color="gray55",
            command=self.destroy,
        ).pack(side="left", padx=8)

        self._build_mouse_fields()

    def _clear_dyn(self):
        for w in self.dyn.winfo_children():
            w.destroy()

    def _lbl(self, text: str, row: int):
        ctk.CTkLabel(self.dyn, text=text, anchor="e", font=FONT_BODY).grid(
            row=row, column=0, padx=10, pady=5, sticky="e"
        )

    # ---------- 各类型字段 ----------

    def _build_mouse_fields(self):
        self._clear_dyn()
        self._lbl("动作:", 0)
        self.mouse_act_var = tk.StringVar(value="click")
        ctk.CTkOptionMenu(
            self.dyn, variable=self.mouse_act_var, values=["click"], font=FONT_BODY
        ).grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        for row, (label, attr, default) in enumerate(
            [("X 坐标:", "x_var", "0"), ("Y 坐标:", "y_var", "0")], start=1
        ):
            self._lbl(label, row)
            setattr(self, attr, tk.StringVar(value=default))
            ctk.CTkEntry(
                self.dyn, textvariable=getattr(self, attr), font=FONT_MONO
            ).grid(row=row, column=1, padx=10, pady=5, sticky="ew")

        self._lbl("鼠标键:", 3)
        self.button_var = tk.StringVar(value="left")
        ctk.CTkOptionMenu(
            self.dyn,
            variable=self.button_var,
            values=["left", "right", "middle"],
            font=FONT_BODY,
        ).grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        self._lbl("点击次数:", 4)
        self.clicks_var = tk.StringVar(value="1")
        ctk.CTkEntry(self.dyn, textvariable=self.clicks_var, font=FONT_MONO).grid(
            row=4, column=1, padx=10, pady=5, sticky="ew"
        )

    def _build_keyboard_fields(self):
        self._clear_dyn()
        self._lbl("动作:", 0)
        self.kb_act_var = tk.StringVar(value="tap")
        ctk.CTkOptionMenu(
            self.dyn,
            variable=self.kb_act_var,
            values=["tap", "press", "hotkey"],
            command=self._on_kb_act_change,
            font=FONT_BODY,
        ).grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        self._lbl("按键:", 1)
        self.key_var = tk.StringVar()
        self.key_entry = ctk.CTkEntry(
            self.dyn,
            textvariable=self.key_var,
            placeholder_text="如: w, space, enter",
            font=FONT_MONO,
        )
        self.key_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        self._lbl("持续时间(s):", 2)
        self.duration_var = tk.StringVar(value="0.1")
        self.dur_entry = ctk.CTkEntry(
            self.dyn, textvariable=self.duration_var, font=FONT_MONO
        )
        self.dur_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

    def _build_delay_fields(self):
        self._clear_dyn()
        self._lbl("延迟时间(s):", 0)
        self.delay_var = tk.StringVar(value="1.0")
        ctk.CTkEntry(self.dyn, textvariable=self.delay_var, font=FONT_MONO).grid(
            row=0, column=1, padx=10, pady=5, sticky="ew"
        )

    def _build_wait_image_fields(self):
        self._clear_dyn()
        self._lbl("模板文件:", 0)
        self.wi_template_var = tk.StringVar()
        templates = list_templates()
        ctk.CTkComboBox(
            self.dyn,
            variable=self.wi_template_var,
            values=templates if templates else ["（无模板）"],
            font=FONT_BODY,
        ).grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        self._lbl("置信度:", 1)
        self.wi_conf_var = tk.StringVar(value="0.8")
        ctk.CTkEntry(self.dyn, textvariable=self.wi_conf_var, font=FONT_MONO).grid(
            row=1, column=1, padx=10, pady=5, sticky="ew"
        )
        self._lbl("超时(s):", 2)
        self.wi_timeout_var = tk.StringVar(value="30")
        ctk.CTkEntry(self.dyn, textvariable=self.wi_timeout_var, font=FONT_MONO).grid(
            row=2, column=1, padx=10, pady=5, sticky="ew"
        )
        self._lbl("检测间隔(s):", 3)
        self.wi_interval_var = tk.StringVar(value="0.5")
        ctk.CTkEntry(self.dyn, textvariable=self.wi_interval_var, font=FONT_MONO).grid(
            row=3, column=1, padx=10, pady=5, sticky="ew"
        )
        self._lbl("区域(留空=全屏):", 4)
        rf = ctk.CTkFrame(self.dyn, fg_color="transparent")
        rf.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        self.wi_rx = tk.StringVar()
        self.wi_ry = tk.StringVar()
        self.wi_rw = tk.StringVar()
        self.wi_rh = tk.StringVar()
        for v, ph in [
            (self.wi_rx, "X"),
            (self.wi_ry, "Y"),
            (self.wi_rw, "W"),
            (self.wi_rh, "H"),
        ]:
            ctk.CTkEntry(
                rf, textvariable=v, placeholder_text=ph, width=52, font=FONT_MONO
            ).pack(side="left", padx=2)

    def _build_if_image_fields(self, t: str):
        self._clear_dyn()
        cond = "存在" if t == "if_image_exist" else "不存在"
        ctk.CTkLabel(
            self.dyn,
            text=f"条件：若模板图像「{cond}」",
            font=FONT_BODY,
            text_color="#5dade2",
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=(8, 4), sticky="w")
        self._lbl("模板文件:", 1)
        self.if_template_var = tk.StringVar()
        templates = list_templates()
        ctk.CTkComboBox(
            self.dyn,
            variable=self.if_template_var,
            values=templates if templates else ["（无模板）"],
            font=FONT_BODY,
        ).grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self._lbl("置信度:", 2)
        self.if_conf_var = tk.StringVar(value="0.8")
        ctk.CTkEntry(self.dyn, textvariable=self.if_conf_var, font=FONT_MONO).grid(
            row=2, column=1, padx=10, pady=5, sticky="ew"
        )
        self._lbl("区域(留空=全屏):", 3)
        rf = ctk.CTkFrame(self.dyn, fg_color="transparent")
        rf.grid(row=3, column=1, padx=10, pady=5, sticky="ew")
        self.if_rx = tk.StringVar()
        self.if_ry = tk.StringVar()
        self.if_rw = tk.StringVar()
        self.if_rh = tk.StringVar()
        for v, ph in [
            (self.if_rx, "X"),
            (self.if_ry, "Y"),
            (self.if_rw, "W"),
            (self.if_rh, "H"),
        ]:
            ctk.CTkEntry(
                rf, textvariable=v, placeholder_text=ph, width=52, font=FONT_MONO
            ).pack(side="left", padx=2)
        self._lbl("then（JSON）:", 4)
        self.then_box = ctk.CTkTextbox(self.dyn, height=80, font=FONT_MONO)
        self.then_box.insert("1.0", "[]")
        self.then_box.grid(row=4, column=1, padx=10, pady=5, sticky="ew")
        self._lbl("else（JSON）:", 5)
        self.else_box = ctk.CTkTextbox(self.dyn, height=80, font=FONT_MONO)
        self.else_box.insert("1.0", "[]")
        self.else_box.grid(row=5, column=1, padx=10, pady=5, sticky="ew")

    # ---------- 事件 ----------

    def _on_type_change(self, val: str):
        self.geometry(self._SIZES.get(val, "440x340"))
        if val == "mouse":
            self._build_mouse_fields()
        elif val == "keyboard":
            self._build_keyboard_fields()
        elif val == "delay":
            self._build_delay_fields()
        elif val == "wait_image":
            self._build_wait_image_fields()
        elif val in ("if_image_exist", "if_image_not_exist"):
            self._build_if_image_fields(val)

    def _on_kb_act_change(self, val: str):
        hint = {
            "hotkey": "如: ctrl+c（用+分隔）",
            "press": "如: w, space",
            "tap": "如: w, space, enter",
        }.get(val, "")
        self.key_entry.configure(placeholder_text=hint)
        self.dur_entry.configure(state="normal" if val == "press" else "disabled")

    # ---------- 数据加载/保存 ----------

    def _load(self):
        t = self.action.get("type", "mouse")
        self.type_var.set(t)
        self._on_type_change(t)
        if t == "mouse":
            self.mouse_act_var.set(self.action.get("action", "click"))
            self.x_var.set(str(self.action.get("x", 0)))
            self.y_var.set(str(self.action.get("y", 0)))
            self.button_var.set(self.action.get("button", "left"))
            self.clicks_var.set(str(self.action.get("clicks", 1)))
        elif t == "keyboard":
            a = self.action.get("action", "tap")
            self.kb_act_var.set(a)
            if a == "hotkey":
                self.key_var.set("+".join(self.action.get("keys", [])))
            else:
                self.key_var.set(self.action.get("key", ""))
            self.duration_var.set(str(self.action.get("duration", 0.1)))
            self._on_kb_act_change(a)
        elif t == "delay":
            self.delay_var.set(str(self.action.get("time", 1.0)))
        elif t == "wait_image":
            self.wi_template_var.set(self.action.get("template", ""))
            self.wi_conf_var.set(str(self.action.get("confidence", 0.8)))
            self.wi_timeout_var.set(str(self.action.get("timeout", 30)))
            self.wi_interval_var.set(str(self.action.get("interval", 0.5)))
            r = self.action.get("region")
            if r and len(r) == 4:
                self.wi_rx.set(str(r[0]))
                self.wi_ry.set(str(r[1]))
                self.wi_rw.set(str(r[2]))
                self.wi_rh.set(str(r[3]))
        elif t in ("if_image_exist", "if_image_not_exist"):
            self.if_template_var.set(self.action.get("template", ""))
            self.if_conf_var.set(str(self.action.get("confidence", 0.8)))
            r = self.action.get("region")
            if r and len(r) == 4:
                self.if_rx.set(str(r[0]))
                self.if_ry.set(str(r[1]))
                self.if_rw.set(str(r[2]))
                self.if_rh.set(str(r[3]))
            self.then_box.delete("1.0", "end")
            self.then_box.insert(
                "1.0",
                json.dumps(self.action.get("then", []), ensure_ascii=False, indent=2),
            )
            self.else_box.delete("1.0", "end")
            self.else_box.insert(
                "1.0",
                json.dumps(self.action.get("else", []), ensure_ascii=False, indent=2),
            )

    def _parse_region(self, rx, ry, rw, rh) -> list | None:
        vals = [rx.get(), ry.get(), rw.get(), rh.get()]
        if not any(vals):
            return None
        return [int(v) if v else 0 for v in vals]

    def _save(self):
        t = self.type_var.get()
        try:
            if t == "mouse":
                act = {
                    "type": "mouse",
                    "action": self.mouse_act_var.get(),
                    "x": int(self.x_var.get()),
                    "y": int(self.y_var.get()),
                    "button": self.button_var.get(),
                    "clicks": int(self.clicks_var.get()),
                    "interval": 0.1,
                }
            elif t == "keyboard":
                a = self.kb_act_var.get()
                if a == "hotkey":
                    keys = [
                        k.strip() for k in self.key_var.get().split("+") if k.strip()
                    ]
                    act = {"type": "keyboard", "action": "hotkey", "keys": keys}
                elif a == "press":
                    act = {
                        "type": "keyboard",
                        "action": "press",
                        "key": self.key_var.get(),
                        "duration": float(self.duration_var.get()),
                    }
                else:
                    act = {
                        "type": "keyboard",
                        "action": "tap",
                        "key": self.key_var.get(),
                    }
            elif t == "delay":
                act = {"type": "delay", "time": float(self.delay_var.get())}
            elif t == "wait_image":
                region = self._parse_region(
                    self.wi_rx, self.wi_ry, self.wi_rw, self.wi_rh
                )
                act = {
                    "type": "wait_image",
                    "template": self.wi_template_var.get(),
                    "confidence": float(self.wi_conf_var.get()),
                    "timeout": float(self.wi_timeout_var.get()),
                    "interval": float(self.wi_interval_var.get()),
                }
                if region:
                    act["region"] = region
            elif t in ("if_image_exist", "if_image_not_exist"):
                region = self._parse_region(
                    self.if_rx, self.if_ry, self.if_rw, self.if_rh
                )
                then_acts = json.loads(self.then_box.get("1.0", "end").strip())
                else_acts = json.loads(self.else_box.get("1.0", "end").strip())
                act = {
                    "type": t,
                    "template": self.if_template_var.get(),
                    "confidence": float(self.if_conf_var.get()),
                    "then": then_acts,
                    "else": else_acts,
                }
                if region:
                    act["region"] = region
            else:
                return
        except (ValueError, json.JSONDecodeError) as e:
            messagebox.showerror("输入错误", f"格式有误：{e}", parent=self)
            return
        self.callback(act)
        self.destroy()


# ═════════════════════════════════════════
# 主应用窗口
# ═════════════════════════════════════════
class GameAutoToolApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("GameAutoTool  v0.2")
        self.geometry("1150x740")
        self.minsize(960, 620)

        # 设置图标
        try:
            _icon = tk.PhotoImage(
                file=os.path.join(os.path.dirname(__file__), "icon.png")
            )
            self.iconphoto(True, _icon)
        except Exception:
            pass

        # ── 核心状态 ──
        self.wm_obj = WindowsManager()
        self.actions: list[dict] = []
        self.running = False
        self._run_thread: threading.Thread | None = None
        self._selected_idx: int | None = None
        self.loop_count = tk.IntVar(value=1)
        self.infinite_loop = tk.BooleanVar(value=False)

        # ── 坐标追踪 ──
        self.tracking = False
        self._track_thread: threading.Thread | None = None
        self._tracker_wm: WindowsManager | None = None
        self._last_rel_x = 0
        self._last_rel_y = 0

        # ── 宏录制 ──
        self.recorder = MacroRecorder()
        self.recorder.set_update_callback(self._on_record_update)

        # ── 定时计划 ──
        self.scheduler = Scheduler()
        self.scheduler.start()

        # ── 全局热键（F8=执行 F9=停止 F10=录制切换）──
        self.hotkey_mgr = HotkeyManager()
        self.hotkey_mgr.register("<f8>", lambda: self.after(0, self._run_actions))
        self.hotkey_mgr.register("<f9>", lambda: self.after(0, self._stop_actions))
        self.hotkey_mgr.register(
            "<f10>", lambda: self.after(0, self._toggle_recording_hotkey)
        )
        try:
            self.hotkey_mgr.start()
        except Exception:
            pass  # 无权限时静默跳过

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ══════════════════════════════════════
    # UI 布局
    # ══════════════════════════════════════

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_topbar()
        self._build_main()
        self._build_statusbar()

    # ── 顶部工具栏 ──
    def _build_topbar(self):
        bar = ctk.CTkFrame(
            self, height=58, corner_radius=0, fg_color=("gray85", "gray17")
        )
        bar.grid(row=0, column=0, sticky="ew")
        bar.grid_columnconfigure(4, weight=1)

        ctk.CTkLabel(
            bar,
            text="⚡ GameAutoTool",
            font=("Microsoft YaHei UI", 17, "bold"),
            text_color=("#1a5276", "#5dade2"),
        ).grid(row=0, column=0, padx=(16, 6), pady=14)

        ctk.CTkLabel(bar, text="│", text_color="gray50").grid(row=0, column=1, padx=4)

        ctk.CTkLabel(bar, text="目标窗口:", font=FONT_BODY).grid(
            row=0, column=2, padx=(8, 4)
        )
        self.win_name_var = tk.StringVar(value="洛克王国：世界  ")
        ctk.CTkEntry(
            bar, textvariable=self.win_name_var, width=200, font=FONT_BODY
        ).grid(row=0, column=3, padx=4)

        ctk.CTkButton(
            bar,
            text="查找并激活",
            width=96,
            font=FONT_BODY,
            fg_color=COLOR_BLUE[0],
            hover_color=COLOR_BLUE[1],
            command=self._find_window,
        ).grid(row=0, column=4, padx=6, sticky="w")

        self.win_status_lbl = ctk.CTkLabel(
            bar, text="● 未连接", text_color="#e74c3c", font=FONT_BODY
        )
        self.win_status_lbl.grid(row=0, column=5, padx=8)

        ctk.CTkLabel(bar, text="│", text_color="gray50").grid(row=0, column=6, padx=4)

        ctk.CTkLabel(
            bar, text="F8=执行  F9=停止  F10=录制", font=FONT_SMALL, text_color="gray50"
        ).grid(row=0, column=7, padx=8)

        ctk.CTkLabel(bar, text="│", text_color="gray50").grid(row=0, column=8, padx=4)

        self.theme_switch = ctk.CTkSwitch(
            bar, text="深色", font=FONT_BODY, command=self._toggle_theme
        )
        self.theme_switch.select()
        self.theme_switch.grid(row=0, column=9, padx=(6, 16))

    # ── 主内容区 ──
    def _build_main(self):
        main = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        main.grid(row=1, column=0, sticky="nsew", padx=8, pady=(4, 0))
        main.grid_columnconfigure(0, weight=0, minsize=340)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        self._build_action_panel(main)
        self._build_right_tabs(main)

    # ── 左侧: 动作列表面板 ──
    def _build_action_panel(self, parent):
        panel = ctk.CTkFrame(parent, corner_radius=10)
        panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        panel.grid_rowconfigure(2, weight=1)
        panel.grid_columnconfigure(0, weight=1)

        # 标题行
        hdr = ctk.CTkFrame(panel, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(hdr, text="动作序列", font=FONT_TITLE).grid(
            row=0, column=0, sticky="w"
        )

        io_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        io_frame.grid(row=0, column=1)
        ctk.CTkButton(
            io_frame,
            text="📂 加载",
            width=68,
            height=26,
            font=FONT_BODY,
            command=self._load_actions,
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            io_frame,
            text="💾 保存",
            width=68,
            height=26,
            font=FONT_BODY,
            command=self._save_actions,
        ).pack(side="left", padx=2)

        # 编辑按钮行
        edit_row = ctk.CTkFrame(panel, fg_color="transparent")
        edit_row.grid(row=1, column=0, sticky="ew", padx=12, pady=(2, 4))

        ctk.CTkButton(
            edit_row,
            text="＋ 添加",
            height=28,
            width=74,
            font=FONT_BODY,
            command=self._add_action,
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            edit_row,
            text="✎ 编辑",
            height=28,
            width=74,
            font=FONT_BODY,
            command=self._edit_action,
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            edit_row,
            text="✕ 删除",
            height=28,
            width=74,
            font=FONT_BODY,
            fg_color=COLOR_RED[0],
            hover_color=COLOR_RED[1],
            command=self._delete_action,
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            edit_row,
            text="↑",
            height=28,
            width=32,
            font=FONT_BODY,
            command=self._move_up,
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            edit_row,
            text="↓",
            height=28,
            width=32,
            font=FONT_BODY,
            command=self._move_down,
        ).pack(side="left", padx=2)

        # 动作列表（Listbox）
        list_wrap = ctk.CTkFrame(panel, fg_color=("gray90", "gray15"), corner_radius=6)
        list_wrap.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)
        list_wrap.grid_rowconfigure(0, weight=1)
        list_wrap.grid_columnconfigure(0, weight=1)

        self.act_lb = tk.Listbox(
            list_wrap,
            selectmode=tk.SINGLE,
            bg="#1e1e2e",
            fg="#cdd6f4",
            selectbackground="#1e66f5",
            selectforeground="#ffffff",
            font=("Consolas", 10),
            relief="flat",
            borderwidth=0,
            activestyle="none",
            highlightthickness=0,
        )
        scrollbar = ctk.CTkScrollbar(list_wrap, command=self.act_lb.yview)
        self.act_lb.configure(yscrollcommand=scrollbar.set)
        self.act_lb.grid(row=0, column=0, sticky="nsew", padx=(4, 0), pady=4)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=4)

        self.act_lb.bind("<<ListboxSelect>>", self._on_select)
        self.act_lb.bind("<Double-Button-1>", lambda e: self._edit_action())

        # 循环控制区
        loop_frame = ctk.CTkFrame(panel, corner_radius=8, fg_color=("gray88", "gray20"))
        loop_frame.grid(row=3, column=0, sticky="ew", padx=12, pady=6)
        loop_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(loop_frame, text="循环次数:", font=FONT_BODY).grid(
            row=0, column=0, padx=10, pady=8
        )
        self.loop_entry = ctk.CTkEntry(
            loop_frame, textvariable=self.loop_count, width=55, font=FONT_MONO
        )
        self.loop_entry.grid(row=0, column=1, padx=6, pady=8, sticky="w")
        ctk.CTkCheckBox(
            loop_frame,
            text="无限循环",
            font=FONT_BODY,
            variable=self.infinite_loop,
            command=self._toggle_infinite,
        ).grid(row=0, column=2, padx=10)

        # 执行 / 停止 按钮
        self.btn_run = ctk.CTkButton(
            panel,
            text="▶  开始执行",
            height=40,
            font=FONT_BOLD,
            fg_color=COLOR_GREEN[0],
            hover_color=COLOR_GREEN[1],
            command=self._run_actions,
        )
        self.btn_run.grid(row=4, column=0, padx=12, pady=(4, 4), sticky="ew")

        self.btn_stop = ctk.CTkButton(
            panel,
            text="■  停止",
            height=40,
            font=FONT_BOLD,
            fg_color=COLOR_RED[0],
            hover_color=COLOR_RED[1],
            state="disabled",
            command=self._stop_actions,
        )
        self.btn_stop.grid(row=5, column=0, padx=12, pady=(0, 12), sticky="ew")

    # ── 右侧：多标签页 ──
    def _build_right_tabs(self, parent):
        self.tabs = ctk.CTkTabview(parent, corner_radius=10)
        self.tabs.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        for name in (
            "🖱  坐标追踪",
            "📸  图像识别",
            "🔴  宏录制",
            "⏱  定时计划",
            "📋  日志",
            "🪟  窗口信息",
        ):
            self.tabs.add(name)

        self._build_tracker_tab(self.tabs.tab("🖱  坐标追踪"))
        self._build_image_tab(self.tabs.tab("📸  图像识别"))
        self._build_recorder_tab(self.tabs.tab("🔴  宏录制"))
        self._build_scheduler_tab(self.tabs.tab("⏱  定时计划"))
        self._build_log_tab(self.tabs.tab("📋  日志"))
        self._build_wininfo_tab(self.tabs.tab("🪟  窗口信息"))

    def _build_tracker_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)

        # 追踪目标窗口输入
        row0 = ctk.CTkFrame(tab, fg_color="transparent")
        row0.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        row0.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(row0, text="追踪窗口:", font=FONT_BODY).grid(
            row=0, column=0, padx=(0, 8)
        )
        self.tracker_win_var = tk.StringVar(value="洛克王国：世界  ")
        ctk.CTkEntry(row0, textvariable=self.tracker_win_var, font=FONT_BODY).grid(
            row=0, column=1, sticky="ew"
        )

        # 坐标展示卡片
        card = ctk.CTkFrame(tab, corner_radius=10, fg_color=("gray88", "gray18"))
        card.grid(row=1, column=0, sticky="ew", padx=10, pady=6)
        card.grid_columnconfigure(1, weight=1)

        def _coord_block(label, attr, row):
            ctk.CTkLabel(card, text=label, font=FONT_BODY, text_color="gray60").grid(
                row=row, column=0, padx=16, pady=10, sticky="w"
            )
            lbl = ctk.CTkLabel(
                card,
                text="(  -  ,  -  )",
                font=("Consolas", 22, "bold"),
                text_color="#5dade2",
            )
            lbl.grid(row=row, column=1, padx=16, pady=10, sticky="w")
            setattr(self, attr, lbl)

        _coord_block("相对坐标", "coord_rel_lbl", 0)
        _coord_block("绝对坐标", "coord_abs_lbl", 1)
        self.coord_abs_lbl.configure(font=("Consolas", 16), text_color="gray50")

        # 快捷操作
        act_row = ctk.CTkFrame(tab, fg_color="transparent")
        act_row.grid(row=2, column=0, sticky="ew", padx=10, pady=4)

        ctk.CTkButton(
            act_row,
            text="📋 复制坐标",
            width=114,
            font=FONT_BODY,
            command=self._copy_coord,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            act_row,
            text="＋ 添加为点击动作",
            font=FONT_BODY,
            command=self._add_coord_as_click,
        ).pack(side="left", padx=4)

        # 追踪开关
        self.btn_track = ctk.CTkButton(
            tab,
            text="▶  开始追踪",
            height=38,
            font=FONT_BOLD,
            fg_color=COLOR_PURPLE[0],
            hover_color=COLOR_PURPLE[1],
            command=self._toggle_tracking,
        )
        self.btn_track.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(
            tab,
            text="提示：开始追踪后将鼠标移到游戏窗口内，坐标实时更新。\n"
            "「相对坐标」是相对于目标窗口左上角的偏移。",
            font=("Microsoft YaHei UI", 10),
            text_color="gray55",
            justify="left",
        ).grid(row=4, column=0, padx=14, pady=(0, 8), sticky="w")

    def _build_log_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        self.log_box = ctk.CTkTextbox(
            tab, font=("Consolas", 10), state="disabled", wrap="word"
        )
        self.log_box.grid(row=0, column=0, sticky="nsew", padx=6, pady=(6, 4))

        ctk.CTkButton(
            tab,
            text="清空日志",
            width=90,
            height=28,
            font=FONT_BODY,
            fg_color="gray40",
            hover_color="gray55",
            command=self._clear_log,
        ).grid(row=1, column=0, pady=(0, 6))

    def _build_wininfo_tab(self, tab):
        tab.grid_columnconfigure(1, weight=1)

        fields = [
            ("窗口标题:", "wi_title"),
            ("窗口类名:", "wi_class"),
            ("位置 (left, top):", "wi_pos"),
            ("尺寸 (width × height):", "wi_size"),
        ]
        self._wi_lbls: dict[str, ctk.CTkLabel] = {}

        for i, (label_text, key) in enumerate(fields):
            ctk.CTkLabel(tab, text=label_text, font=FONT_BODY, anchor="e").grid(
                row=i, column=0, padx=16, pady=12, sticky="e"
            )
            lbl = ctk.CTkLabel(
                tab, text="—", font=("Consolas", 11), text_color="#5dade2", anchor="w"
            )
            lbl.grid(row=i, column=1, padx=16, pady=12, sticky="w")
            self._wi_lbls[key] = lbl

        ctk.CTkButton(
            tab, text="↻  刷新", width=90, font=FONT_BODY, command=self._refresh_wininfo
        ).grid(row=len(fields), column=0, columnspan=2, pady=12)

    # ── 图像识别 标签 ──

    def _build_image_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # 模板目录路径行
        path_row = ctk.CTkFrame(tab, fg_color="transparent")
        path_row.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        path_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(path_row, text="模板目录:", font=FONT_BODY).grid(
            row=0, column=0, padx=(0, 6)
        )
        ctk.CTkLabel(
            path_row,
            text=TEMPLATES_DIR,
            font=FONT_SMALL,
            text_color="gray55",
            anchor="w",
        ).grid(row=0, column=1, sticky="ew")
        ctk.CTkButton(
            path_row,
            text="📂 打开",
            width=70,
            height=26,
            font=FONT_BODY,
            command=lambda: os.startfile(TEMPLATES_DIR),
        ).grid(row=0, column=2, padx=(6, 0))

        # 截取保存模板区域
        cap_frame = ctk.CTkFrame(tab, corner_radius=8, fg_color=("gray88", "gray20"))
        cap_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=4)
        cap_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(cap_frame, text="── 截取新模板 ──", font=FONT_BOLD).grid(
            row=0, column=0, columnspan=4, padx=12, pady=(8, 4), sticky="w"
        )

        ctk.CTkLabel(cap_frame, text="文件名:", font=FONT_BODY).grid(
            row=1, column=0, padx=10, pady=5
        )
        self.cap_name_var = tk.StringVar(value="template.png")
        ctk.CTkEntry(cap_frame, textvariable=self.cap_name_var, font=FONT_MONO).grid(
            row=1, column=1, padx=6, pady=5, sticky="ew"
        )

        ctk.CTkLabel(cap_frame, text="区域 X/Y/W/H:", font=FONT_BODY).grid(
            row=2, column=0, padx=10, pady=5
        )
        region_row = ctk.CTkFrame(cap_frame, fg_color="transparent")
        region_row.grid(row=2, column=1, sticky="ew", padx=6)
        self.cap_rx = tk.StringVar()
        self.cap_ry = tk.StringVar()
        self.cap_rw = tk.StringVar()
        self.cap_rh = tk.StringVar()
        for v, ph in [
            (self.cap_rx, "X"),
            (self.cap_ry, "Y"),
            (self.cap_rw, "W"),
            (self.cap_rh, "H"),
        ]:
            ctk.CTkEntry(
                region_row,
                textvariable=v,
                placeholder_text=ph,
                width=56,
                font=FONT_MONO,
            ).pack(side="left", padx=3)

        ctk.CTkButton(
            cap_frame,
            text="📷 3秒后截取并保存",
            font=FONT_BODY,
            command=self._capture_template,
        ).grid(row=3, column=0, columnspan=2, padx=12, pady=(4, 10), sticky="w")

        # 模板列表 + 操作
        list_frame = ctk.CTkFrame(tab, corner_radius=8, fg_color=("gray88", "gray20"))
        list_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=4)
        list_frame.grid_rowconfigure(1, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        hdr2 = ctk.CTkFrame(list_frame, fg_color="transparent")
        hdr2.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        hdr2.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr2, text="模板文件列表", font=FONT_BOLD).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkButton(
            hdr2,
            text="↻ 刷新",
            width=64,
            height=26,
            font=FONT_BODY,
            command=self._refresh_templates,
        ).grid(row=0, column=1, padx=4)

        lb_wrap = ctk.CTkFrame(
            list_frame, fg_color=("gray92", "gray16"), corner_radius=4
        )
        lb_wrap.grid(row=1, column=0, sticky="nsew", padx=10, pady=4)
        lb_wrap.grid_rowconfigure(0, weight=1)
        lb_wrap.grid_columnconfigure(0, weight=1)

        self.tmpl_lb = tk.Listbox(
            lb_wrap,
            selectmode=tk.SINGLE,
            bg="#1e1e2e",
            fg="#cdd6f4",
            selectbackground="#1e66f5",
            font=("Consolas", 10),
            relief="flat",
            borderwidth=0,
            activestyle="none",
            highlightthickness=0,
        )
        tmpl_sb = ctk.CTkScrollbar(lb_wrap, command=self.tmpl_lb.yview)
        self.tmpl_lb.configure(yscrollcommand=tmpl_sb.set)
        self.tmpl_lb.grid(row=0, column=0, sticky="nsew", padx=(4, 0), pady=4)
        tmpl_sb.grid(row=0, column=1, sticky="ns", pady=4)

        btn_row = ctk.CTkFrame(list_frame, fg_color="transparent")
        btn_row.grid(row=2, column=0, padx=10, pady=(4, 10))
        ctk.CTkButton(
            btn_row, text="🔍 测试检测", font=FONT_BODY, command=self._test_detect
        ).pack(side="left", padx=4)
        self.detect_conf_var = tk.StringVar(value="0.8")
        ctk.CTkEntry(
            btn_row,
            textvariable=self.detect_conf_var,
            width=50,
            placeholder_text="置信",
            font=FONT_MONO,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            btn_row,
            text="🗑 删除",
            font=FONT_BODY,
            fg_color=COLOR_RED[0],
            hover_color=COLOR_RED[1],
            command=self._delete_template,
        ).pack(side="left", padx=4)

        self._refresh_templates()

    # ── 宏录制 标签 ──

    def _build_recorder_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # 状态卡片
        state_card = ctk.CTkFrame(tab, corner_radius=10, fg_color=("gray88", "gray18"))
        state_card.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        state_card.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(state_card, text="录制状态:", font=FONT_BODY).grid(
            row=0, column=0, padx=12, pady=10
        )
        self.rec_status_lbl = ctk.CTkLabel(
            state_card, text="● 未录制", text_color="#e74c3c", font=FONT_BOLD
        )
        self.rec_status_lbl.grid(row=0, column=1, padx=8, pady=10, sticky="w")
        self.rec_count_lbl = ctk.CTkLabel(
            state_card, text="已录 0 个动作", font=FONT_BODY, text_color="gray55"
        )
        self.rec_count_lbl.grid(row=0, column=2, padx=12, pady=10)

        ctk.CTkLabel(
            state_card,
            text="鼠标坐标偏移与「目标窗口」自动同步 · 过滤 F8/F9/F10 键",
            font=FONT_SMALL,
            text_color="gray55",
        ).grid(row=1, column=0, columnspan=3, padx=12, pady=(0, 8), sticky="w")

        # 开始/停止录制
        self.btn_record = ctk.CTkButton(
            tab,
            text="⏺  开始录制  (F10)",
            height=40,
            font=FONT_BOLD,
            fg_color=COLOR_ORANGE[0],
            hover_color=COLOR_ORANGE[1],
            command=self._toggle_recording,
        )
        self.btn_record.grid(row=1, column=0, padx=10, pady=6, sticky="ew")

        # 录制预览
        preview_frame = ctk.CTkFrame(
            tab, corner_radius=8, fg_color=("gray88", "gray20")
        )
        preview_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=4)
        preview_frame.grid_rowconfigure(1, weight=1)
        preview_frame.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(preview_frame, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="录制预览（最近录入）", font=FONT_BOLD).grid(
            row=0, column=0, sticky="w"
        )

        self.rec_preview = ctk.CTkTextbox(
            preview_frame, font=("Consolas", 10), state="disabled", wrap="none"
        )
        self.rec_preview.grid(row=1, column=0, sticky="nsew", padx=10, pady=4)

        op_row = ctk.CTkFrame(preview_frame, fg_color="transparent")
        op_row.grid(row=2, column=0, padx=10, pady=(4, 10))
        ctk.CTkButton(
            op_row,
            text="✓ 导入到动作列表",
            font=FONT_BODY,
            fg_color=COLOR_GREEN[0],
            hover_color=COLOR_GREEN[1],
            command=self._import_recording,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            op_row,
            text="🗑 清空录制",
            font=FONT_BODY,
            fg_color="gray40",
            hover_color="gray55",
            command=self._clear_recording,
        ).pack(side="left", padx=4)

    # ── 定时计划 标签 ──

    def _build_scheduler_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        sch_bar = ctk.CTkFrame(tab, corner_radius=8, fg_color=("gray88", "gray20"))
        sch_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        sch_bar.grid_columnconfigure(1, weight=1)

        self.sch_status_lbl = ctk.CTkLabel(
            sch_bar, text="🟢 调度器运行中", text_color="#2ecc71", font=FONT_BOLD
        )
        self.sch_status_lbl.grid(row=0, column=0, padx=12, pady=10, sticky="w")

        ctk.CTkLabel(
            sch_bar,
            text="格式：HH:MM（每天定时）/ 30s（每30秒）/ 5m（每5分钟）/ 2h（每2小时）",
            font=FONT_SMALL,
            text_color="gray55",
        ).grid(row=0, column=1, padx=8)

        list_frame = ctk.CTkFrame(tab, corner_radius=8, fg_color=("gray88", "gray20"))
        list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=4)
        list_frame.grid_rowconfigure(1, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)

        hdr = ctk.CTkFrame(list_frame, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=10, pady=(8, 4))
        hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(hdr, text="计划任务列表", font=FONT_BOLD).grid(
            row=0, column=0, sticky="w"
        )
        ctk.CTkButton(
            hdr,
            text="↻ 刷新",
            width=64,
            height=26,
            font=FONT_BODY,
            command=self._refresh_schedule_list,
        ).grid(row=0, column=1, padx=4)

        self.sch_lb = tk.Listbox(
            list_frame,
            selectmode=tk.SINGLE,
            bg="#1e1e2e",
            fg="#cdd6f4",
            selectbackground="#1e66f5",
            font=("Consolas", 10),
            relief="flat",
            borderwidth=0,
            activestyle="none",
            highlightthickness=0,
        )
        sch_sb = ctk.CTkScrollbar(list_frame, command=self.sch_lb.yview)
        self.sch_lb.configure(yscrollcommand=sch_sb.set)
        self.sch_lb.grid(row=1, column=0, sticky="nsew", padx=(10, 0), pady=4)
        sch_sb.grid(row=1, column=1, sticky="ns", padx=(0, 6), pady=4)

        lb_btns = ctk.CTkFrame(list_frame, fg_color="transparent")
        lb_btns.grid(row=2, column=0, columnspan=2, padx=10, pady=(4, 8))
        ctk.CTkButton(
            lb_btns,
            text="⏸ 启用/禁用",
            font=FONT_BODY,
            command=self._toggle_selected_task,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            lb_btns,
            text="🗑 删除",
            font=FONT_BODY,
            fg_color=COLOR_RED[0],
            hover_color=COLOR_RED[1],
            command=self._delete_selected_task,
        ).pack(side="left", padx=4)

        add_frame = ctk.CTkFrame(tab, corner_radius=8, fg_color=("gray88", "gray20"))
        add_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=4)
        add_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(add_frame, text="── 添加新计划 ──", font=FONT_BOLD).grid(
            row=0, column=0, columnspan=2, padx=12, pady=(8, 4), sticky="w"
        )
        ctk.CTkLabel(add_frame, text="任务说明:", font=FONT_BODY).grid(
            row=1, column=0, padx=10, pady=6, sticky="e"
        )
        self.sch_desc_var = tk.StringVar()
        ctk.CTkEntry(
            add_frame,
            textvariable=self.sch_desc_var,
            font=FONT_BODY,
            placeholder_text="如：每日回血",
        ).grid(row=1, column=1, padx=8, pady=6, sticky="ew")
        ctk.CTkLabel(add_frame, text="时间规格:", font=FONT_BODY).grid(
            row=2, column=0, padx=10, pady=6, sticky="e"
        )
        self.sch_time_var = tk.StringVar()
        ctk.CTkEntry(
            add_frame,
            textvariable=self.sch_time_var,
            width=120,
            font=FONT_MONO,
            placeholder_text="18:00 / 30s",
        ).grid(row=2, column=1, padx=8, pady=6, sticky="w")
        ctk.CTkButton(
            add_frame,
            text="➕ 添加（执行当前动作列表）",
            font=FONT_BODY,
            fg_color=COLOR_TEAL[0],
            hover_color=COLOR_TEAL[1],
            command=self._add_schedule_task,
        ).grid(row=3, column=0, columnspan=2, padx=12, pady=(4, 12), sticky="w")

    # ── 底部状态栏 ──
    def _build_statusbar(self):
        bar = ctk.CTkFrame(
            self, height=26, corner_radius=0, fg_color=("gray80", "gray15")
        )
        bar.grid(row=2, column=0, sticky="ew")
        bar.grid_columnconfigure(0, weight=1)

        self.status_lbl = ctk.CTkLabel(
            bar,
            text="就绪",
            font=FONT_SMALL,
            anchor="w",
            text_color="gray60",
        )
        self.status_lbl.grid(row=0, column=0, padx=12, pady=3, sticky="w")

    # ══════════════════════════════════════
    # 日志 & 状态
    # ══════════════════════════════════════

    def _log(self, msg: str):
        timestamp = time.strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"[{timestamp}]  {msg}\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        self.status_lbl.configure(text=msg)

    def _safe_log(self, msg: str):
        self.after(0, lambda: self._log(msg))

    def _clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    # ══════════════════════════════════════
    # 窗口管理
    # ══════════════════════════════════════

    def _find_window(self):
        name = self.win_name_var.get()
        if not name.strip():
            return
        self.wm_obj = WindowsManager()
        if not self.wm_obj.find_window(name, None):
            self.win_status_lbl.configure(text="● 未找到", text_color="#e74c3c")
            self._log(f"未找到窗口：{name}")
            return
        self.wm_obj.bring_to_foreground()
        self.win_status_lbl.configure(text="● 已连接", text_color="#2ecc71")
        self._log(
            f"已激活窗口：{name}  位置({self.wm_obj.left}, {self.wm_obj.top})  "
            f"尺寸 {self.wm_obj.width}×{self.wm_obj.height}"
        )
        self.recorder.set_window_offset(self.wm_obj.left or 0, self.wm_obj.top or 0)
        self._refresh_wininfo()

    def _refresh_wininfo(self):
        w = self.wm_obj
        if not w.hwnd:
            return
        self._wi_lbls["wi_title"].configure(text=w.window_name or "—")
        self._wi_lbls["wi_class"].configure(text=w.class_name or "—")
        if w.left is not None:
            self._wi_lbls["wi_pos"].configure(text=f"({w.left}, {w.top})")
            self._wi_lbls["wi_size"].configure(text=f"{w.width} × {w.height}")

    # ══════════════════════════════════════
    # 动作列表管理
    # ══════════════════════════════════════

    def _action_desc(self, act: dict) -> str:
        t = act.get("type", "?")
        if t == "mouse":
            return (
                f"[🖱 鼠标] {act.get('action','?')}  "
                f"({act.get('x','?')}, {act.get('y','?')})  "
                f"{act.get('button','left')} ×{act.get('clicks',1)}"
            )
        elif t == "keyboard":
            a = act.get("action", "?")
            if a == "hotkey":
                return f"[⌨ 键盘] 组合键  {' + '.join(act.get('keys', []))}"
            dur = f"  {act.get('duration', 0):.1f}s" if a == "press" else ""
            return f"[⌨ 键盘] {a}  「{act.get('key','?')}」{dur}"
        elif t == "delay":
            return f"[⏱ 延迟] {act.get('time', 0)}s"
        elif t == "wait_image":
            return (
                f"[⏳ 等图像] {act.get('template','?')}  "
                f"置信:{act.get('confidence',0.8)}  超时:{act.get('timeout',30)}s"
            )
        elif t in ("if_image_exist", "if_image_not_exist"):
            cond = "存在" if t == "if_image_exist" else "不存在"
            tn = len(act.get("then", []))
            en = len(act.get("else", []))
            return f"[🔀 若{cond}] {act.get('template','?')}  then:{tn}  else:{en}"
        return f"[?] {t}"

    def _refresh_list(self):
        self.act_lb.delete(0, tk.END)
        for i, act in enumerate(self.actions):
            self.act_lb.insert(tk.END, f"  {i+1:2d}.  {self._action_desc(act)}")

    def _on_select(self, _event=None):
        sel = self.act_lb.curselection()
        self._selected_idx = sel[0] if sel else None

    def _add_action(self):
        ActionDialog(self, None, lambda a: self._on_action_saved(a))

    def _edit_action(self):
        idx = self._selected_idx
        if idx is None or idx >= len(self.actions):
            messagebox.showinfo("提示", "请先在列表中选择一个动作", parent=self)
            return
        ActionDialog(self, self.actions[idx], lambda a: self._on_action_saved(a, idx))

    def _on_action_saved(self, act: dict, idx: int | None = None):
        if idx is None:
            self.actions.append(act)
        else:
            self.actions[idx] = act
        self._refresh_list()

    def _delete_action(self):
        idx = self._selected_idx
        if idx is None or idx >= len(self.actions):
            return
        self.actions.pop(idx)
        self._selected_idx = None
        self._refresh_list()

    def _move_up(self):
        idx = self._selected_idx
        if idx is None or idx <= 0:
            return
        self.actions[idx - 1], self.actions[idx] = (
            self.actions[idx],
            self.actions[idx - 1],
        )
        self._selected_idx = idx - 1
        self._refresh_list()
        self.act_lb.selection_set(self._selected_idx)

    def _move_down(self):
        idx = self._selected_idx
        if idx is None or idx >= len(self.actions) - 1:
            return
        self.actions[idx + 1], self.actions[idx] = (
            self.actions[idx],
            self.actions[idx + 1],
        )
        self._selected_idx = idx + 1
        self._refresh_list()
        self.act_lb.selection_set(self._selected_idx)

    def _load_actions(self):
        path = filedialog.askopenfilename(
            title="加载动作文件",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                raise ValueError("文件格式错误，应为 JSON 数组")
            self.actions = data
            self._refresh_list()
            self._log(f"已加载 {len(self.actions)} 个动作：{os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("加载失败", str(e), parent=self)

    def _save_actions(self):
        path = filedialog.asksaveasfilename(
            title="保存动作文件",
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.actions, f, indent=2, ensure_ascii=False)
            self._log(f"已保存 {len(self.actions)} 个动作：{os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("保存失败", str(e), parent=self)

    def _toggle_infinite(self):
        self.loop_entry.configure(
            state="disabled" if self.infinite_loop.get() else "normal"
        )

    # ══════════════════════════════════════
    # 执行控制
    # ══════════════════════════════════════

    def _run_actions(self):
        if not self.actions:
            messagebox.showinfo("提示", "动作列表为空，请先添加动作", parent=self)
            return
        if not self.wm_obj.hwnd:
            messagebox.showwarning(
                "警告", "请先点击「查找并激活」以连接目标窗口", parent=self
            )
            return

        self.running = True
        self.btn_run.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self._run_thread = threading.Thread(target=self._run_worker, daemon=True)
        self._run_thread.start()

    def _run_worker(self):
        total = float("inf") if self.infinite_loop.get() else self.loop_count.get()
        loop = 0
        try:
            self.wm_obj.bring_to_foreground()
            self._safe_log(
                f"▶ 开始执行，共 {'∞' if self.infinite_loop.get() else int(total)} 轮"
            )
            while self.running and loop < total:
                loop += 1
                self._safe_log(f"── 第 {loop} 轮 ──")
                for i, act in enumerate(self.actions):
                    if not self.running:
                        break
                    self._safe_log(f"  [{i+1}] {self._action_desc(act)}")
                    try:
                        if act["type"] == "mouse":
                            move.handle_mouse(act, self.wm_obj.left, self.wm_obj.top)
                        elif act["type"] == "keyboard":
                            move.handle_keyboard(act)
                        elif act["type"] == "delay":
                            time.sleep(act["time"])
                    except Exception as e:
                        self._safe_log(f"  ⚠ 出错：{e}")
                if self.running and loop < total:
                    time.sleep(0.05)
        finally:
            self.running = False
            self.after(0, self._run_done)

    def _run_done(self):
        self.btn_run.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self._log("■ 执行完毕")

    def _stop_actions(self):
        self.running = False
        self._log("■ 已手动停止")

    # ══════════════════════════════════════
    # 坐标追踪
    # ══════════════════════════════════════

    def _toggle_tracking(self):
        if not self.tracking:
            self._start_tracking()
        else:
            self._stop_tracking()

    def _start_tracking(self):
        win_name = self.tracker_win_var.get().strip()
        tracker_wm = None

        if win_name:
            wm = WindowsManager()
            if wm.find_window(win_name, None):
                wm.bring_to_foreground()
                tracker_wm = wm
                self._log(f"坐标追踪：已锁定窗口「{win_name}」")
            else:
                self._log(f"坐标追踪：未找到窗口「{win_name}」，显示绝对坐标")

        self._tracker_wm = tracker_wm
        self.tracking = True
        self.btn_track.configure(
            text="■  停止追踪", fg_color=COLOR_RED[0], hover_color=COLOR_RED[1]
        )
        self._track_thread = threading.Thread(target=self._track_worker, daemon=True)
        self._track_thread.start()

    def _stop_tracking(self):
        self.tracking = False
        self.btn_track.configure(
            text="▶  开始追踪", fg_color=COLOR_PURPLE[0], hover_color=COLOR_PURPLE[1]
        )

    def _track_worker(self):
        while self.tracking:
            ax, ay = pyautogui.position()
            tw = self._tracker_wm
            if tw and tw.left is not None:
                rx, ry = ax - tw.left, ay - tw.top
            else:
                rx, ry = ax, ay
            self._last_rel_x, self._last_rel_y = rx, ry
            self.after(
                0,
                lambda rx=rx, ry=ry, ax=ax, ay=ay: self._update_coord_labels(
                    rx, ry, ax, ay
                ),
            )
            time.sleep(0.05)

    def _update_coord_labels(self, rx, ry, ax, ay):
        self.coord_rel_lbl.configure(text=f"({rx:4d}, {ry:4d})")
        self.coord_abs_lbl.configure(text=f"({ax:4d}, {ay:4d})")

    def _copy_coord(self):
        coord = f"{self._last_rel_x}, {self._last_rel_y}"
        self.clipboard_clear()
        self.clipboard_append(coord)
        self._log(f"已复制坐标：({coord})")

    def _add_coord_as_click(self):
        act = {
            "type": "mouse",
            "action": "click",
            "x": self._last_rel_x,
            "y": self._last_rel_y,
            "button": "left",
            "clicks": 1,
            "interval": 0.1,
        }
        self.actions.append(act)
        self._refresh_list()
        self._log(f"已添加点击动作：({self._last_rel_x}, {self._last_rel_y})")

    # ══════════════════════════════════════
    # 主题 & 关闭
    # ══════════════════════════════════════

    def _toggle_theme(self):
        mode = "dark" if self.theme_switch.get() else "light"
        ctk.set_appearance_mode(mode)
        self.theme_switch.configure(text="深色" if mode == "dark" else "浅色")

    def _on_close(self):
        self.tracking = False
        self.running = False
        if self.recorder.recording:
            self.recorder.stop()
        self.scheduler.stop()
        self.hotkey_mgr.stop()
        self.destroy()

    # ══════════════════════
    # 图像识别
    # ══════════════════════

    def _refresh_templates(self):
        self.tmpl_lb.delete(0, tk.END)
        for fn in list_templates():
            self.tmpl_lb.insert(tk.END, f"  {fn}")

    def _get_selected_template(self) -> str | None:
        sel = self.tmpl_lb.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一个模板", parent=self)
            return None
        return self.tmpl_lb.get(sel[0]).strip()

    def _capture_template(self):
        filename = self.cap_name_var.get().strip()
        if not filename:
            messagebox.showwarning("警告", "请输入文件名", parent=self)
            return
        try:
            vals = [
                self.cap_rx.get(),
                self.cap_ry.get(),
                self.cap_rw.get(),
                self.cap_rh.get(),
            ]
            region = [int(v) if v else 0 for v in vals] if any(vals) else None
        except ValueError:
            messagebox.showerror("错误", "区域坐标必须为整数", parent=self)
            return
        self._log("📷 3秒后截取，请切换到游戏窗口...")
        self.after(3000, lambda: self._do_capture(region, filename))

    def _do_capture(self, region, filename):
        try:
            path = save_template(region, filename)
            self._log(f"✅ 模板已保存：{os.path.basename(path)}")
            self._refresh_templates()
        except Exception as e:
            self._log(f"截取失败：{e}")

    def _test_detect(self):
        tmpl = self._get_selected_template()
        if not tmpl:
            return
        try:
            conf = float(self.detect_conf_var.get())
        except ValueError:
            conf = 0.8
        self._log(f"🔍 检测中：{tmpl}  置信度阈值 {conf}")

        def _worker():
            try:
                result = find_on_screen(tmpl, None, conf)
                if result:
                    self._safe_log(
                        f"  ✅ 找到 {tmpl}  位置({result[0]}, {result[1]})  置信度 {result[2]:.3f}"
                    )
                else:
                    self._safe_log(f"  ✗ 未找到 {tmpl}（置信度不足）")
            except Exception as e:
                self._safe_log(f"  检测出错：{e}")

        threading.Thread(target=_worker, daemon=True).start()

    def _delete_template(self):
        tmpl = self._get_selected_template()
        if not tmpl:
            return
        if messagebox.askyesno("确认", f"删除模板文件 {tmpl}？", parent=self):
            try:
                os.remove(os.path.join(TEMPLATES_DIR, tmpl))
                self._refresh_templates()
                self._log(f"已删除模板：{tmpl}")
            except Exception as e:
                messagebox.showerror("删除失败", str(e), parent=self)

    # ══════════════════════
    # 宏录制
    # ══════════════════════

    def _toggle_recording(self):
        if not self.recorder.recording:
            self._start_recording()
        else:
            self._stop_recording()

    def _toggle_recording_hotkey(self):
        """F10 触发，在主线程调用"""
        self._toggle_recording()

    def _start_recording(self):
        if self.wm_obj.left is not None:
            self.recorder.set_window_offset(self.wm_obj.left, self.wm_obj.top)
        self.recorder.start()
        self.btn_record.configure(
            text="⏹  停止录制  (F10)", fg_color=COLOR_RED[0], hover_color=COLOR_RED[1]
        )
        self.rec_status_lbl.configure(text="● 录制中", text_color="#e74c3c")
        self._log("⏺ 宏录制已开始")

    def _stop_recording(self):
        self.recorder.stop()
        self.btn_record.configure(
            text="⏺  开始录制  (F10)",
            fg_color=COLOR_ORANGE[0],
            hover_color=COLOR_ORANGE[1],
        )
        self.rec_status_lbl.configure(text="● 已停止", text_color="#f39c12")
        self._log(f"⏹ 宏录制停止，共录制 {len(self.recorder.actions)} 个动作")

    def _on_record_update(self, actions: list):
        """pynput 线程回调 → 派发到主线程"""
        self.after(0, lambda: self._update_rec_preview(actions))

    def _update_rec_preview(self, actions: list):
        n = len(actions)
        self.rec_count_lbl.configure(text=f"已录 {n} 个动作")
        start = max(0, n - 30)
        lines = [
            f"  {start+i+1:3d}.  {self._action_desc(a)}"
            for i, a in enumerate(actions[start:])
        ]
        self.rec_preview.configure(state="normal")
        self.rec_preview.delete("1.0", "end")
        self.rec_preview.insert("1.0", "\n".join(lines))
        self.rec_preview.see("end")
        self.rec_preview.configure(state="disabled")

    def _import_recording(self):
        acts = list(self.recorder.actions)
        if not acts:
            messagebox.showinfo("提示", "录制列表为空", parent=self)
            return
        self.actions.extend(acts)
        self._refresh_list()
        self._log(f"已导入 {len(acts)} 个录制动作")

    def _clear_recording(self):
        self.recorder.actions.clear()
        self.rec_count_lbl.configure(text="已录 0 个动作")
        self.rec_preview.configure(state="normal")
        self.rec_preview.delete("1.0", "end")
        self.rec_preview.configure(state="disabled")

    # ══════════════════════
    # 定时计划
    # ══════════════════════

    def _add_schedule_task(self):
        desc = self.sch_desc_var.get().strip()
        spec = self.sch_time_var.get().strip()
        if not desc or not spec:
            messagebox.showwarning("警告", "请填写任务说明和时间规格", parent=self)
            return
        if not self.actions:
            messagebox.showwarning("警告", "当前动作列表为空", parent=self)
            return
        snapshot = list(self.actions)

        def _task_cb():
            if not self.wm_obj.hwnd:
                self._safe_log(f"[定时] {desc}：未连接窗口，跳过")
                return
            self._safe_log(f"[定时] ▶ {desc}")
            move.execute_actions(
                snapshot,
                win_left=self.wm_obj.left or 0,
                win_top=self.wm_obj.top or 0,
                log_fn=self._safe_log,
                stop_check=lambda: not self.scheduler.is_running(),
            )
            self._safe_log(f"[定时] ■ {desc} 执行完毕")

        try:
            task = ScheduledTask(desc, spec, _task_cb)
            self.scheduler.add_task(task)
            self._log(f"已添加计划：{desc} [{spec}]")
            self._refresh_schedule_list()
        except ValueError as e:
            messagebox.showerror("错误", str(e), parent=self)

    def _refresh_schedule_list(self):
        self.sch_lb.delete(0, tk.END)
        for task in self.scheduler.get_tasks():
            mark = "✓" if task.enabled else "✗"
            self.sch_lb.insert(
                tk.END,
                f"  [{mark}]  {task.time_spec:<8}  {task.description}  "
                f"已执行 {task.run_count} 次  上次 {task.last_run}  ID:{task.task_id}",
            )

    def _get_selected_task_id(self) -> str | None:
        sel = self.sch_lb.curselection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一个任务", parent=self)
            return None
        line = self.sch_lb.get(sel[0])
        return line.split("ID:")[-1].strip() if "ID:" in line else None

    def _toggle_selected_task(self):
        tid = self._get_selected_task_id()
        if not tid:
            return
        tasks = {t.task_id: t for t in self.scheduler.get_tasks()}
        if tid in tasks:
            t = tasks[tid]
            self.scheduler.toggle_task(tid, not t.enabled)
            self._log(
                f"计划 {t.description} 已{'\u542f用' if not t.enabled else '\u7981用'}"
            )
            self._refresh_schedule_list()

    def _delete_selected_task(self):
        tid = self._get_selected_task_id()
        if not tid:
            return
        self.scheduler.remove_task(tid)
        self._log(f"已删除计划 ID:{tid}")
        self._refresh_schedule_list()


# ─────────────────────────────────────────
# 入口
# ─────────────────────────────────────────
if __name__ == "__main__":
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = GameAutoToolApp()
    app.mainloop()
