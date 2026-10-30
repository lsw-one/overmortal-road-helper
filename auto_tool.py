import tkinter as tk
import tkinter.messagebox
import customtkinter as ctk
import subprocess
import cv2
import numpy as np
import threading
import time
import os
import sys
import json
import webbrowser
import ctypes # 用于处理高分辨率缩放
import random # 用于随机偏移防检测

# ================= 配置区域 =================
IMAGE_CONFIDENCE = 0.65       
LOOP_DELAY = 0.05            
BASE_WIDTH = 1660
BASE_HEIGHT = 2560
CONFIG_FILE = "config.json"
CLICK_OFFSET = 8  
STUCK_TIMEOUT = 180 # 超过多少秒未点击判定为卡死（3分钟）

SIMING_NAMES = {
    1: "气血/真元", 2: "物攻/法攻", 3: "物防/法防",
    4: "会心/倍率", 5: "会心抗性", 6: "怪物增伤",
    7: "神通增伤", 8: "法宝增伤", 9: "古宝增伤"
}

SIMING_COORDS = {
    1: (440, 683), 2: (820, 683), 3: (1203, 683),
    4: (426, 1230), 5: (822, 1230), 6: (1200, 1230),
    7: (436, 1776), 8: (817, 1776), 9: (1200, 1776)
}

REWARD_CLOSE_POS = (840, 1814)  
SIMING_CLOSE_POS = (840, 2100)  
DAILY_CHECKBOX_OFFSET_X = 57
# ============================================

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
    APP_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DIR = BASE_DIR

ICON_PATH = os.path.join(BASE_DIR, "assets", "icon.ico")
if not os.path.exists(ICON_PATH):
    ICON_PATH = os.path.join(BASE_DIR, "icon.ico")

if os.path.exists(os.path.join(BASE_DIR, "adb", "adb.exe")):
    ADB_PATH = os.path.join(BASE_DIR, "adb", "adb.exe")
    ADB_CWD = os.path.join(BASE_DIR, "adb")
elif os.path.exists(os.path.join(BASE_DIR, "adb.exe")):
    ADB_PATH = os.path.join(BASE_DIR, "adb.exe")
    ADB_CWD = BASE_DIR
else:
    ADB_PATH = os.path.join(BASE_DIR, "adb", "adb.exe") 
    ADB_CWD = BASE_DIR

if os.path.exists(os.path.join(BASE_DIR, "assets", "images")):
    IMG_DIR = os.path.join(BASE_DIR, "assets", "images")
else:
    IMG_DIR = os.path.join(BASE_DIR, "images")

CONFIG_PATH = os.path.join(APP_DIR, CONFIG_FILE)

FONT_FAMILY = "Microsoft YaHei UI" 
LOG_FONT = "Cascadia Code" if os.name == 'nt' else "Consolas"

# ================= 主题色定义：(light, dark) 元组 =================
THEME_BG      = ("#ebebeb", "#242424")
THEME_FRAME   = ("#dbdbdb", "#2b2b2b")
THEME_ROW     = ("#ffffff", "#2f2f2f")
THEME_TEXT    = ("#1a1a1a", "#dce4ee")
THEME_ENTRY   = ("#f9f9fa", "#343638")
THEME_BORDER  = ("#979da2", "#565b5e")
THEME_LOG_BG  = ("#ffffff", "#1e1e1e")
THEME_LOG_TX  = ("#333333", "#d4d4d4")

def get_img_path(filename):
    direct_path = os.path.join(IMG_DIR, filename)
    if os.path.exists(direct_path):
        return direct_path
    base_name = os.path.basename(filename)
    for root, dirs, files in os.walk(IMG_DIR):
        if base_name in files:
            return os.path.join(root, base_name)
    return direct_path

# ================= 颜色工具 =================
def _hex_to_rgb(h):
    h = h.lstrip('#')
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)

def _rgb_to_hex(r, g, b):
    return f"#{int(round(r)):02x}{int(round(g)):02x}{int(round(b)):02x}"

def _lerp_color(c1, c2, t):
    r1, g1, b1 = _hex_to_rgb(c1)
    r2, g2, b2 = _hex_to_rgb(c2)
    return _rgb_to_hex(r1 + (r2 - r1) * t,
                       g1 + (g2 - g1) * t,
                       b1 + (b2 - b1) * t)

# ================= 深色标题栏工具 =================
def apply_titlebar(window, dark=True):
    if os.name != 'nt':
        return
    try:
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        if not hwnd:
            hwnd = window.winfo_id()
        value = ctypes.c_int(1 if dark else 0)
        for attr in (20, 19):
            try:
                res = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, attr, ctypes.byref(value), ctypes.sizeof(value)
                )
                if res == 0:
                    break
            except Exception:
                pass
    except Exception:
        pass

# ================= 遮罩式主题切换器 =================
class ThemeSwitcher:
    def __init__(self, app):
        self.app = app
        self.root = app.root
        self.active = False

    def switch(self, to_dark, fade_in_ms=120, color_ms=260, fade_out_ms=140):
        if self.active:
            return
        self.active = True

        if to_dark:
            from_bg, to_bg = THEME_BG[0], THEME_BG[1]
        else:
            from_bg, to_bg = THEME_BG[1], THEME_BG[0]

        overlay = tk.Toplevel(self.root)
        overlay.withdraw()
        overlay.overrideredirect(True)
        try:
            overlay.attributes("-topmost", True)
        except Exception:
            pass

        self.root.update_idletasks()
        x = self.root.winfo_rootx()
        y = self.root.winfo_rooty()
        w = self.root.winfo_width()
        h = self.root.winfo_height()

        overlay.geometry(self._geom(w, h, x, y))
        overlay.configure(bg=from_bg)

        has_alpha = False
        try:
            overlay.attributes("-alpha", 0.0)
            has_alpha = True
        except Exception:
            pass

        overlay.deiconify()
        try:
            overlay.update_idletasks()
        except Exception:
            pass

        if has_alpha:
            self._fade_in(overlay, 0, max(1, fade_in_ms // 15),
                          to_dark, from_bg, to_bg, color_ms, fade_out_ms)
        else:
            self._do_switch(overlay, False, to_dark, from_bg, to_bg,
                            color_ms, fade_out_ms)

    @staticmethod
    def _geom(w, h, x, y):
        xs = f"{x:+d}" if x != 0 else "+0"
        ys = f"{y:+d}" if y != 0 else "+0"
        return f"{w}x{h}{xs}{ys}"

    def _fade_in(self, overlay, i, total, to_dark, from_bg, to_bg,
                 color_ms, fade_out_ms):
        if i > total:
            try:
                overlay.attributes("-alpha", 1.0)
            except Exception:
                pass
            self._do_switch(overlay, True, to_dark, from_bg, to_bg,
                            color_ms, fade_out_ms)
            return
        try:
            overlay.attributes("-alpha", i / total)
        except Exception:
            pass
        self.root.after(15, self._fade_in, overlay, i + 1, total,
                        to_dark, from_bg, to_bg, color_ms, fade_out_ms)

    def _do_switch(self, overlay, has_alpha, to_dark, from_bg, to_bg,
                   color_ms, fade_out_ms):
        ctk.set_appearance_mode("dark" if to_dark else "light")
        try:
            self.root.update_idletasks()
            self.root.update()
        except Exception:
            pass

        frames = max(5, color_ms // 15)
        def step_color(i):
            if i >= frames:
                self._fade_out(overlay, has_alpha, to_bg, fade_out_ms)
                return
            t = i / frames
            try:
                overlay.configure(bg=_lerp_color(from_bg, to_bg, t))
            except Exception:
                pass
            self.root.after(15, step_color, i + 1)
        step_color(0)

    def _fade_out(self, overlay, has_alpha, to_bg, fade_out_ms):
        if not has_alpha:
            self._finish(overlay)
            return
        total = max(1, fade_out_ms // 15)
        def step(i):
            if i > total:
                self._finish(overlay)
                return
            try:
                overlay.attributes("-alpha", 1.0 - i / total)
            except Exception:
                pass
            self.root.after(15, step, i + 1)
        step(0)

    def _finish(self, overlay):
        try:
            overlay.destroy()
        except Exception:
            pass
        self.active = False
        is_dark = ctk.get_appearance_mode() == "Dark"
        apply_titlebar(self.root, is_dark)
        for child in self.root.winfo_children():
            if isinstance(child, SettingsWindow):
                try:
                    apply_titlebar(child, is_dark)
                except Exception:
                    pass

# ================= 设置窗口类（整行平滑滑动版） =================
class SettingsWindow(ctk.CTkToplevel):
    CARD_H = 40
    ROW_GAP = 12
    COL_GAP = 10
    ANIM_FRAMES = 12
    ANIM_INTERVAL = 16

    def __init__(self, master, main_app):
        super().__init__(master)
        self.main_app = main_app
        self.card_widgets = {}
        self.animating = False
        self._last_container_size = None

        self.title("域外古路助手 - 设置")

        w, h = 560, 740
        self.geometry(f"{w}x{h}+-9999+-9999")

        if os.path.exists(ICON_PATH):
            self.iconbitmap(ICON_PATH)

        self.configure(fg_color=THEME_BG)

        # --- ADB 端口 ---
        dev_frame = ctk.CTkFrame(self, fg_color=THEME_FRAME)
        dev_frame.pack(fill="x", padx=20, pady=10)

        ctk.CTkLabel(dev_frame, text="ADB 端口:", font=(FONT_FAMILY, 14),
                     text_color=THEME_TEXT).grid(row=0, column=0, padx=10, pady=10)

        self.port_entry = ctk.CTkEntry(dev_frame, width=100, font=(FONT_FAMILY, 14),
                                       justify="center",
                                       fg_color=THEME_ENTRY,
                                       border_color=THEME_BORDER,
                                       text_color=THEME_TEXT)
        self.port_entry.insert(0, main_app.adb_port)
        self.port_entry.grid(row=0, column=1, padx=10)

        ctk.CTkLabel(dev_frame, text="(具体查看在模拟器里)", text_color="gray",
                     font=(FONT_FAMILY, 12)).grid(row=0, column=2, padx=(0, 10))

        # --- 优先级标题 ---
        ctk.CTkLabel(self, text="【司命道碑】优先级设置",
                     font=(FONT_FAMILY, 16, "bold"),
                     text_color=THEME_TEXT).pack(pady=(5, 5))

        input_frame = ctk.CTkFrame(self, fg_color="transparent")
        input_frame.pack(pady=5)

        self.entry_var = tk.StringVar(value=",".join(str(x) for x in main_app.current_priority))
        self.priority_entry = ctk.CTkEntry(input_frame, textvariable=self.entry_var,
                                           width=250, justify="center",
                                           font=(FONT_FAMILY, 14),
                                           fg_color=THEME_ENTRY,
                                           border_color=THEME_BORDER,
                                           text_color=THEME_TEXT)
        self.priority_entry.pack(side="left", padx=10)

        ctk.CTkButton(input_frame, text="应用输入", width=80,
                      font=(FONT_FAMILY, 13),
                      command=self.sync_from_entry).pack(side="left")

        # --- 属性参照表 ---
        help_frame = ctk.CTkFrame(self, fg_color=THEME_FRAME)
        help_frame.pack(pady=5, fill="x", padx=20)

        ctk.CTkLabel(help_frame, text="属性编号参照",
                     font=(FONT_FAMILY, 13, "bold"),
                     text_color=THEME_TEXT).pack(pady=2)

        grid_frame = ctk.CTkFrame(help_frame, fg_color="transparent")
        grid_frame.pack(padx=5, pady=(0, 5))
        items = [
            "1:气血/真元", "2:物攻/法攻", "3:物防/法防",
            "4:会心/倍率", "5:会心抗性", "6:怪物增伤",
            "7:神通增伤", "8:法宝增伤", "9:古宝增伤"
        ]
        for index, text in enumerate(items):
            ctk.CTkLabel(grid_frame, text=text, font=(FONT_FAMILY, 13),
                         text_color=THEME_TEXT).grid(
                row=index // 3, column=index % 3, padx=15, pady=3)

        # --- 执行顺序标题 ---
        ctk.CTkLabel(self, text="当前执行顺序 (点击箭头调整)",
                     font=(FONT_FAMILY, 14, "bold"),
                     text_color=THEME_TEXT).pack(pady=(5, 0))

        self.list_frame = ctk.CTkFrame(self, fg_color=THEME_BG)
        self.list_frame.pack(fill="both", expand=True, padx=20, pady=5)

        self.render_priority_list()

        ctk.CTkButton(self, text="保存并关闭", width=180, height=40,
                      font=(FONT_FAMILY, 15, "bold"),
                      command=self.save_and_close).pack(pady=10)

        # --- 底部信息 ---
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(fill="x", side="bottom", padx=20, pady=(0, 5))

        author_label = ctk.CTkLabel(
            info_frame,
            text="作者: lsw-one | GitHub: overmortal-road-helper",
            text_color="#3a7ebf", cursor="hand2",
            font=(FONT_FAMILY, 12, "underline"))
        author_label.pack(pady=(5, 2))
        author_label.bind("<Button-1>",
                          lambda e: webbrowser.open("https://github.com/lsw-one/overmortal-road-helper"))

        disclaimer_text = "本软件仅供学习交流与个人护肝使用，严禁商业盈利。\n使用本软件产生的一切后果由使用者自行承担。"
        ctk.CTkLabel(info_frame, text=disclaimer_text, text_color="gray",
                     font=(FONT_FAMILY, 11), justify="center").pack(pady=(0, 5))

        self.update_idletasks()

        mx = master.winfo_rootx()
        my = master.winfo_rooty()
        mw = master.winfo_width()
        mh = master.winfo_height()
        x = mx + (mw - w) // 2
        y = my + (mh - h) // 2
        if x < 0: x = 0
        if y < 0: y = 0

        self.geometry(f"{w}x{h}+{x}+{y}")
        self.transient(master)
        self.lift()
        self.focus_force()
        self.after(50, self.grab_set)
        self.after(80, lambda: apply_titlebar(self, ctk.get_appearance_mode() == "Dark"))

    def render_priority_list(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        self.card_widgets.clear()
        self._last_container_size = None

        self.container = ctk.CTkFrame(self.list_frame, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=5, pady=5)
        self.container.bind("<Configure>", self._on_container_resize)

        for num in range(1, 10):
            frame = ctk.CTkFrame(self.container, fg_color=THEME_ROW, corner_radius=8)

            label = ctk.CTkLabel(frame, text="", font=(FONT_FAMILY, 13), anchor="w",
                                 fg_color="transparent", text_color=THEME_TEXT)
            label.pack(side="left", fill="x", expand=True, padx=(10, 10))

            down_btn = ctk.CTkButton(frame, text="▼", width=30, height=26,
                                     fg_color="#555555", hover_color="#777777",
                                     command=lambda n=num: self._move_card(n, 1))
            down_btn.pack(side="right", padx=2)

            up_btn = ctk.CTkButton(frame, text="▲", width=30, height=26,
                                   fg_color="#555555", hover_color="#777777",
                                   command=lambda n=num: self._move_card(n, -1))
            up_btn.pack(side="right", padx=2)

            self.card_widgets[num] = {
                'frame': frame,
                'label': label,
                'up': up_btn,
                'down': down_btn,
            }

        self.after(20, lambda: self._layout_cards())

    def _on_container_resize(self, event):
        if self.animating:
            return
        if event.width < 50 or event.height < 50:
            return
        if self._last_container_size == (event.width, event.height):
            return
        self._last_container_size = (event.width, event.height)
        self._layout_cards(container_w=event.width)

    def _layout_cards(self, container_w=None):
        if self.animating:
            return
        if container_w is None:
            try:
                container_w = self.container.winfo_width()
            except Exception:
                return
        if container_w < 50:
            self.after(30, lambda: self._layout_cards())
            return

        col_w = (container_w - self.COL_GAP) // 2

        for pos, num in enumerate(self.main_app.current_priority):
            if num not in self.card_widgets:
                continue
            x, y, _ = self._pos_to_xy(pos, container_w)
            fw = self.card_widgets[num]['frame']
            tk.Place.place(fw, x=x, y=y, width=col_w, height=self.CARD_H)

        self._refresh_all_items()

    def _pos_to_xy(self, pos, container_w):
        col_w = (container_w - self.COL_GAP) // 2
        row_h = self.CARD_H + self.ROW_GAP
        col = 0 if pos < 5 else 1
        row = pos if pos < 5 else pos - 5
        return col * (col_w + self.COL_GAP), row * row_h, col_w

    def _refresh_all_items(self):
        priority = self.main_app.current_priority
        n = len(priority)
        for pos, num in enumerate(priority):
            if num not in self.card_widgets:
                continue
            card = self.card_widgets[num]
            name = SIMING_NAMES.get(num, "未知")
            card['label'].configure(text=f"{pos+1}. {name}")
            
            is_first = (pos == 0)
            is_last = (pos == n - 1)
            card['up'].configure(state="disabled" if is_first else "normal")
            card['down'].configure(state="disabled" if is_last else "normal")

    def _set_buttons_enabled(self, enabled):
        for cw in self.card_widgets.values():
            cw['up'].configure(state="normal" if enabled else "disabled")
            cw['down'].configure(state="normal" if enabled else "disabled")

    @staticmethod
    def _ease_in_out(t):
        if t < 0.5:
            return 2 * t * t
        return 1 - (-2 * t + 2) ** 2 / 2

    def _move_card(self, num, direction):
        if self.animating:
            return
        priority = self.main_app.current_priority
        try:
            pos = priority.index(num)
        except ValueError:
            return
        new_pos = pos + direction
        if not (0 <= new_pos < len(priority)):
            return
        self._animate_swap(pos, new_pos)

    def _animate_swap(self, pos_i, pos_j):
        try:
            container_w = self.container.winfo_width()
        except Exception:
            return
        priority = self.main_app.current_priority

        if container_w < 50:
            priority[pos_i], priority[pos_j] = priority[pos_j], priority[pos_i]
            self._layout_cards()
            self.update_entry_from_list()
            return

        num_i = priority[pos_i]
        num_j = priority[pos_j]
        if num_i not in self.card_widgets or num_j not in self.card_widgets:
            return

        xi, yi, card_w = self._pos_to_xy(pos_i, container_w)
        xj, yj, _ = self._pos_to_xy(pos_j, container_w)

        card_i = self.card_widgets[num_i]['frame']
        card_j = self.card_widgets[num_j]['frame']

        if yi < yj:
            card_i.lift()
        else:
            card_j.lift()

        self.animating = True
        self._set_buttons_enabled(False)

        total = self.ANIM_FRAMES

        def step(k):
            if not self.winfo_exists():
                return
            if k > total:
                tk.Place.place(card_i, x=xj, y=yj, width=card_w, height=self.CARD_H)
                tk.Place.place(card_j, x=xi, y=yi, width=card_w, height=self.CARD_H)
                priority[pos_i], priority[pos_j] = num_j, num_i
                self.animating = False
                self._refresh_all_items()
                self.update_entry_from_list()
                return

            t = self._ease_in_out(k / total)
            tk.Place.place(card_i, x=xi + (xj - xi) * t,
                           y=yi + (yj - yi) * t,
                           width=card_w, height=self.CARD_H)
            tk.Place.place(card_j, x=xj + (xi - xj) * t,
                           y=yj + (yi - yj) * t,
                           width=card_w, height=self.CARD_H)
            self.after(self.ANIM_INTERVAL, step, k + 1)

        step(0)

    def sync_from_entry(self):
        try:
            raw_text = self.entry_var.get()
            nums = [int(x.strip()) for x in raw_text.replace("，", ",").split(",")
                    if x.strip().isdigit()]
            valid_nums = []
            for n in nums:
                if 1 <= n <= 9 and n not in valid_nums:
                    valid_nums.append(n)
            for i in range(1, 10):
                if i not in valid_nums:
                    valid_nums.append(i)
            self.main_app.current_priority = valid_nums[:9]
            self._layout_cards()
        except Exception:
            tkinter.messagebox.showerror("错误", "输入格式有误，请用逗号分隔数字(1-9)", parent=self)

    def update_entry_from_list(self):
        self.entry_var.set(",".join(str(x) for x in self.main_app.current_priority))

    def save_and_close(self):
        self.main_app.adb_port = self.port_entry.get().strip()
        config_data = {
            "adb_port": self.main_app.adb_port,
            "priority_list": self.main_app.current_priority
        }
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
            self.main_app.add_log(f"【系统】 设置已保存到 {CONFIG_PATH}")
        except Exception as e:
            tkinter.messagebox.showerror("保存失败", f"无法保存配置文件：{e}", parent=self)
        self.destroy()

# ================= 主界面类 =================
class GameAutomationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("一念逍遥·域外古路助手 v2.1")

        w, h = 570, 680
        self.root.update_idletasks()
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = (ws - w) // 2
        y = (hs - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        self.root.minsize(540, 600)
        self.root.resizable(True, True)

        if os.path.exists(ICON_PATH):
            self.root.iconbitmap(ICON_PATH)

        self.is_running = False
        self.is_paused = False
        self.thread = None

        self.is_auto_challenging = False
        self.force_challenge_next = False
        self.force_auto_next = False
        self.check_siming_now = False

        self.last_click_time = 0
        self.last_click_pos = (0, 0)
        self.current_state = ""
        self.fail_count = 0
        
        self.last_action_time = time.time() 
        self.alert_triggered = False

        self.adb_port = "16448"
        self.current_priority = [4, 2, 6, 1, 5, 8, 7, 9, 3]
        self.img_cache = {}

        self.theme_switcher = ThemeSwitcher(self)

        self.root.configure(fg_color=THEME_BG)

        # 顶部栏
        top_frame = ctk.CTkFrame(root, fg_color="transparent")
        top_frame.pack(fill="x", padx=20, pady=(15, 0))

        ctk.CTkLabel(top_frame, text="域外古路助手",
                     font=(FONT_FAMILY, 22, "bold"),
                     text_color=THEME_TEXT).pack(side="left")

        set_btn = ctk.CTkButton(top_frame, text="⚙️ 设置", width=70, height=30,
                                font=(FONT_FAMILY, 13), command=self.open_settings)
        set_btn.pack(side="right", padx=(10, 0))

        self.theme_btn = ctk.CTkButton(top_frame, text="🌗 切换主题", width=90, height=30,
                                       font=(FONT_FAMILY, 13), fg_color="gray",
                                       hover_color="#555555", command=self.toggle_theme)
        self.theme_btn.pack(side="right")

        # 状态区
        self.status_label = ctk.CTkLabel(root, text="状态：未启动",
                                         font=(FONT_FAMILY, 18, "bold"),
                                         text_color="#e67e22")
        self.status_label.pack(pady=20)

        # 按钮区
        btn_frame = ctk.CTkFrame(root, fg_color="transparent")
        btn_frame.pack(pady=10)

        self.start_btn = ctk.CTkButton(btn_frame, text="开启后台挂机", width=130, height=40,
                                       font=(FONT_FAMILY, 15, "bold"), fg_color="#2ecc71",
                                       hover_color="#27ae60", text_color="black",
                                       command=self.start_task)
        self.start_btn.pack(side="left", padx=10)

        self.pause_btn = ctk.CTkButton(btn_frame, text="暂停", width=80, height=40,
                                       font=(FONT_FAMILY, 15, "bold"), fg_color="#f1c40f",
                                       hover_color="#f39c12", text_color="black",
                                       state="disabled", command=self.toggle_pause)
        self.pause_btn.pack(side="left", padx=10)

        self.stop_btn = ctk.CTkButton(btn_frame, text="停止运行", width=100, height=40,
                                      font=(FONT_FAMILY, 15, "bold"), fg_color="#e74c3c",
                                      hover_color="#c0392b", text_color="black",
                                      state="disabled", command=self.stop_task)
        self.stop_btn.pack(side="left", padx=10)

        # 日志区
        log_frame = ctk.CTkFrame(root, fg_color="transparent")
        log_frame.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        ctk.CTkLabel(log_frame, text="操作日志", font=(FONT_FAMILY, 14, "bold"),
                     text_color=THEME_TEXT).pack(anchor="w")

        self.log_text = ctk.CTkTextbox(log_frame, font=(LOG_FONT, 14), state="disabled",
                                       fg_color=THEME_LOG_BG, text_color=THEME_LOG_TX)
        self.log_text.pack(fill="both", expand=True, pady=(5, 0))

        self.load_config()
        self.root.after(100, self.preload_images)
        self.root.after(500, self.check_files)
        self.root.after(150, lambda: apply_titlebar(self.root, ctk.get_appearance_mode() == "Dark"))

    def toggle_theme(self):
        if self.theme_switcher.active:
            return
        to_dark = ctk.get_appearance_mode() != "Dark"
        self.add_log("【系统】 切换到深色模式..." if to_dark else "【系统】 切换到浅色模式...")
        self.theme_switcher.switch(to_dark)

    def preload_images(self):
        count = 0
        for root, dirs, files in os.walk(IMG_DIR):
            for file in files:
                if file.lower().endswith(".png"):
                    full_path = os.path.join(root, file)
                    template = cv2.imdecode(np.fromfile(full_path, dtype=np.uint8),
                                            cv2.IMREAD_COLOR)
                    if template is not None:
                        self.img_cache[file] = template
                        self.img_cache[file + "_gray"] = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
                        count += 1
        self.add_log(f"【系统】 成功预加载 {count} 张图片至内存")

    def check_files(self):
        if not os.path.exists(ADB_PATH):
            self.add_log(f"❌ 严重错误：找不到 adb.exe！\n请检查路径: {ADB_PATH}")
        else:
            self.add_log(f"✅ ADB 工具就绪 ({ADB_CWD})")

        test_img = get_img_path('btn_challenge.png')
        if not os.path.exists(test_img):
            self.add_log(f"❌ 严重错误：找不到图片！\n请检查图片文件夹: {IMG_DIR}")
        else:
            self.add_log(f"✅ 图片资源就绪 ({IMG_DIR})")

    def load_config(self):
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.adb_port = data.get("adb_port", "16448")
                    priority = data.get("priority_list", [4, 2, 6, 1, 5, 8, 7, 9, 3])
                    if isinstance(priority, list) and len(priority) == 9:
                        self.current_priority = priority
                self.add_log(f"【系统】 已成功加载配置文件: {CONFIG_PATH}")
            except Exception:
                self.add_log(f"【系统】 读取配置失败，将使用默认值")
        else:
            self.add_log(f"【系统】 未找到配置文件，将使用默认端口和排序")

    def open_settings(self):
        for child in self.root.winfo_children():
            if isinstance(child, SettingsWindow):
                child.focus_set()
                return
        SettingsWindow(self.root, self)

    def add_log(self, msg, color=None):
        self.root.after(0, self._append_log, msg, color)

    def _append_log(self, msg, color=None):
        current_time = time.strftime("%H:%M:%S")
        self.log_text.configure(state="normal")

        if color:
            tag_name = f"tag_{color.replace('#', '')}"
            self.log_text.tag_config(tag_name, foreground=color)
            self.log_text.insert("end", f"[{current_time}] {msg}\n", tag_name)
        else:
            self.log_text.insert("end", f"[{current_time}] {msg}\n")

        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def update_status(self, text, color):
        self.root.after(0, self._update_status_ui, text, color)
        if text != self.current_state and "扫描中" not in text:
            self.add_log(f"【状态】 {text}")
        self.current_state = text

    def _update_status_ui(self, text, color):
        if self.is_running or "停止" in text:
            self.status_label.configure(text=f"状态：{text}", text_color=color)

    def safe_sleep(self, seconds):
        start_t = time.time()
        while time.time() - start_t < seconds:
            if not self.is_running:
                return
            while self.is_paused and self.is_running:
                time.sleep(0.05)
            time.sleep(0.05)

    def _wait_if_paused(self):
        while self.is_paused and self.is_running:
            time.sleep(0.05)
        return self.is_running

    def adb_screenshot(self):
        if not self._wait_if_paused():
            return None
        current_port = f"127.0.0.1:{self.adb_port}"
        cmd = f'"{ADB_PATH}" -s {current_port} exec-out screencap -p'
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True,
                                    startupinfo=startupinfo, cwd=ADB_CWD, timeout=2)
            if result.returncode != 0 or not result.stdout:
                return None
            img_bytes = np.frombuffer(result.stdout, np.uint8)
            return cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
        except Exception:
            return None

    def adb_click(self, x, y):
        if not self._wait_if_paused():
            return
        current_time = time.time()
        
        if abs(x - self.last_click_pos[0]) < 10 and abs(y - self.last_click_pos[1]) < 10:
            if current_time - self.last_click_time < 0.5:
                return
        self.last_click_pos = (x, y)
        self.last_click_time = current_time
        
        self.last_action_time = time.time()
        self.alert_triggered = False

        offset_x = random.randint(-CLICK_OFFSET, CLICK_OFFSET)
        offset_y = random.randint(-CLICK_OFFSET, CLICK_OFFSET)
        actual_x = x + offset_x
        actual_y = y + offset_y

        current_port = f"127.0.0.1:{self.adb_port}"
        cmd = f'"{ADB_PATH}" -s {current_port} shell input tap {actual_x} {actual_y}'
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, startupinfo=startupinfo, cwd=ADB_CWD)

    def flash_taskbar(self):
        if os.name != 'nt':
            return
            
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if not hwnd:
                hwnd = self.root.winfo_id()
                
            class FLASHWINFO(ctypes.Structure):
                _fields_ = [('cbSize', ctypes.c_uint),
                            ('hwnd', ctypes.c_void_p),
                            ('dwFlags', ctypes.c_uint),
                            ('uCount', ctypes.c_uint),
                            ('dwTimeout', ctypes.c_uint)]
            
            fw = FLASHWINFO()
            fw.cbSize = ctypes.sizeof(FLASHWINFO)
            fw.hwnd = hwnd
            fw.dwFlags = 3 | 12 
            fw.uCount = 0
            fw.dwTimeout = 0
            ctypes.windll.user32.FlashWindowEx(ctypes.byref(fw))
        except Exception:
            pass

    def rescue_step(self):
        """单次抢救动作：根据识别到的特征，执行一步脱困操作"""
        screen = self.adb_screenshot()
        if screen is None:
            return
        curr_h, curr_w = screen.shape[:2]

        # 1. 处理日常弹窗
        if self.find_image_match(screen, 'icon_daily_no_prompt.png')[0]:
            self.add_log("【抢救】 发现日常弹窗，强制处理", "#e67e22")
            self.handle_daily_popup(screen, curr_w, curr_h)
            return

        # 2. 处理无奖励弹窗
        if self.find_image_match(screen, 'icon_no_reward.png')[0]:
            self.add_log("【抢救】 发现无奖励弹窗，强制关闭", "#e67e22")
            self.wait_and_close_popup('icon_no_reward.png', 1.0, int(804 * (curr_w / BASE_WIDTH)), int(1980 * (curr_h / BASE_HEIGHT)), action_name="无奖励")
            return

        # 3. 处理领奖/恭喜获得
        if self.find_image_match(screen, 'btn_claim.png')[0] or self.find_image_match(screen, 'text_congrats.png')[0]:
            self.add_log("【抢救】 发现领奖/恭喜获得特征，强制关闭", "#e67e22")
            self.wait_and_close_popup('text_congrats.png', 1.0, int(805 * (curr_w / BASE_WIDTH)), int(1870 * (curr_h / BASE_HEIGHT)), action_name="恭喜获得")
            return

        # 4. 处理战斗失败/胜利/Buff界面
        if self.find_image_match(screen, 'btn_fail.png')[0]:
            self.add_log("【抢救】 发现失败界面，点击空白", "#e67e22")
            self.adb_click(curr_w // 2, int(curr_h * 0.30))
            return

        if self.find_image_match(screen, 'btn_win.png')[0] or self.find_image_match(screen, 'icon_heart.png')[0]:
            self.add_log("【抢救】 发现胜利/选Buff特征，盲点中心", "#e67e22")
            self.adb_click(int(curr_w * 0.505), int(curr_h * 0.409))
            self.adb_click(int(curr_w * 0.505), int(curr_h * 0.745))
            return

        # 5. 处理道宝/司命界面（只要确认了在这俩界面，就放心点返回）
        if self.find_image_match(screen, 'text_upgrade_success.png')[0] or \
           self.find_image_match(screen, 'daobao/popup_lingye.png')[0] or \
           self.find_image_match(screen, 'daobao/zaohua/zaohua_inside.png')[0] or \
           self.find_image_match(screen, 'daobao/pangu/pangu_inside.png')[0] or \
           self.find_image_match(screen, 'btn_select_residue.png')[0] or \
           self.find_image_match(screen, 'btn_siming_no_dot.png')[0]:
            
            self.add_log("【抢救】 确认在道宝/司命界面，点击返回", "#e67e22")
            if self.find_and_click(screen, 'btn_back.png'):
                return

        # 如果啥也匹配不上，干等
        self.add_log("【抢救】 未识别到任何已知特征，等待画面变化...", "#e67e22")

    def watchdog_thread(self):
        while self.is_running:
            if not self.is_paused:
                if time.time() - self.last_action_time > STUCK_TIMEOUT:
                    if not self.alert_triggered:
                        # ★ 触发时：只记日志，不闪烁
                        self.add_log(f"⚠️ 超过 {STUCK_TIMEOUT//60} 分钟未操作，正在后台尝试故障抢救...", "#e67e22")
                        self.alert_triggered = True
                        
                        rescue_start_time = time.time()
                        rescued = False
                        
                        while self.is_running and (time.time() - rescue_start_time < 60):
                            if not self._wait_if_paused():
                                break
                                
                            # 判断是否回到主界面
                            screen = self.adb_screenshot()
                            if screen is not None:
                                if self.find_image_safe(screen, 'btn_challenge.png', min_conf=0.85, min_bright=20)[0] or \
                                   self.find_image_safe(screen, 'btn_auto.png', min_conf=0.75, min_bright=40)[0] or \
                                   self.find_image_safe(screen, 'daobao/entry.png', min_conf=0.85, min_bright=40)[0]: 
                                    self.add_log("【抢救】 已确认回到挑战主界面！抢救结束。", "#2ecc71")
                                    rescued = True
                                    break
                                    
                            self.rescue_step()
                            self.safe_sleep(2.0)
                            
                        # ★ 结果判定
                        if rescued:
                            self.last_action_time = time.time()
                            self.alert_triggered = False
                        else:
                            # ★ 只有抢救彻底失败，才闪烁报警并暂停
                            self.add_log("❌ 抢救超过1分钟仍未回到主界面，自动暂停脚本", "#e74c3c")
                            self.flash_taskbar()
                            self.root.after(0, self.toggle_pause, True)
            time.sleep(5)

    def find_image_match(self, screen_img, img_name, use_gray=False, custom_confidence=None):
        base_name = os.path.basename(img_name)
        cache_key = base_name + ("_gray" if use_gray else "")
        template = self.img_cache.get(cache_key)
        if template is None:
            return None, 0, None

        target_screen = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY) if use_gray else screen_img
        result = cv2.matchTemplate(target_screen, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        threshold = custom_confidence if custom_confidence is not None else IMAGE_CONFIDENCE

        if max_val >= threshold:
            h, w = template.shape[:2]
            return ((max_loc[0] + w // 2, max_loc[1] + h // 2), max_val, (max_loc[0], max_loc[1], w, h))
        return None, max_val, None

    def find_image_safe(self, screen_img, img_name, min_conf=0.7, min_bright=0):
        loc, max_val, rect = self.find_image_match(screen_img, img_name, custom_confidence=min_conf)
        if not loc:
            return None, max_val
        
        x, y, w, h = rect
        crop = screen_img[y:y+h, x:x+w]
        if crop.size == 0:
            return None, max_val
            
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        mean_b = np.mean(gray)
        if mean_b < min_bright:
            return None, max_val
            
        return loc, max_val

    # ★ 新增：等待特定文字出现，并闭环关闭弹窗
    def wait_and_close_popup(self, text_img, wait_time, close_x, close_y, action_name="弹窗"):
        self.add_log(f"【系统】 等待 [{action_name}] 出现 (最多 {wait_time} 秒)...")
        start_t = time.time()
        found = False
        
        # 1. 等待文字出现
        while time.time() - start_t < wait_time:
            if not self.is_running: return
            screen = self.adb_screenshot()
            if screen is not None:
                loc, _, _ = self.find_image_match(screen, text_img, custom_confidence=0.7)
                if loc:
                    found = True
                    break
            self.safe_sleep(0.3)
        
        # 2. 执行关闭动作（如果没找到也去点一下，作为兜底）
        if not found:
            self.add_log(f"【系统】 未识别到 [{action_name}] 文字，直接执行坐标点击", "#e67e22")
        else:
            self.add_log(f"【操作】 发现 [{action_name}]，准备点击坐标关闭")

        for i in range(2):
            self.adb_click(close_x, close_y)
            self.safe_sleep(1.0)
            
            screen = self.adb_screenshot()
            if screen is None: return
            loc, _, _ = self.find_image_match(screen, text_img, custom_confidence=0.7)
            if not loc:
                self.add_log(f"【系统】 [{action_name}] 已成功关闭")
                return
            else:
                self.add_log(f"【系统】 [{action_name}] 未消失，重试点击", "#e67e22")
                
        self.add_log(f"【系统】 多次点击仍无法关闭 [{action_name}]，放弃", "#e74c3c")

    def check_siming_with_dot(self, screen):
        loc, val, rect = self.find_image_match(screen, 'btn_siming_no_dot.png')
        if rect is None:
            return False, None
        base_x, base_y, w, h = rect
        dot_region = screen[max(0, base_y - 30):min(screen.shape[0], base_y + 60),
                            max(0, base_x + w - 60):min(screen.shape[1], base_x + w + 40)]
        dot_loc, dot_val, _ = self.find_image_match(dot_region, 'icon_red_dot.png')
        if dot_loc:
            return True, (base_x + w // 2, base_y + h // 2)
        return False, None

    def find_and_click(self, screen_img, img_name):
        loc, _, _ = self.find_image_match(screen_img, img_name)
        if loc:
            self.adb_click(loc[0], loc[1])
            return True
        return False

    # ------------------ 专属状态机 ------------------
    def fast_track_main_ui(self, timeout=4.0):
        start_t = time.time()
        while self.is_running and time.time() - start_t < timeout:
            if not self._wait_if_paused():
                return "stopped"

            scr = self.adb_screenshot()
            if scr is None:
                self.safe_sleep(0.05)
                continue

            if self.find_image_match(scr, 'icon_daily_no_prompt.png')[0]:
                return "popup"
                
            # ★ 修复：如果极速通道里看到了领奖弹窗、无奖励、恭喜获得、升阶成功，直接退出，交回主循环处理
            if self.find_image_match(scr, 'btn_claim.png')[0] or \
               self.find_image_match(scr, 'icon_no_reward.png')[0] or \
               self.find_image_match(scr, 'text_congrats.png')[0] or \
               self.find_image_match(scr, 'text_upgrade_success.png')[0]:
                return "timeout"

            c_loc, _ = self.find_image_safe(scr, 'btn_challenge.png', min_conf=0.8, min_bright=20)
            if c_loc:
                self.update_status("进入极速通道", "#2ecc71")
                self.add_log("【操作】 极速通道点击【前往挑战】")
                self.adb_click(c_loc[0], c_loc[1])
                self.update_status("正在等待战斗加载...", "#2ecc71")
                # ★ 动态等待
                for _ in range(8):
                    self.safe_sleep(0.5)
                    chk = self.adb_screenshot()
                    if chk is None or not self.find_image_safe(chk, 'btn_challenge.png', min_conf=0.85, min_bright=25)[0]:
                        break
                return "challenge"
            self.safe_sleep(0.05)
        return "timeout"

    def handle_buff_loop(self, curr_w, curr_h):
        self.update_status("处理 Buff 界面", "#9b59b6")
        start_t = time.time()

        while self.is_running and time.time() - start_t < 10.0:
            if not self._wait_if_paused():
                return

            screen = self.adb_screenshot()
            if screen is None:
                self.safe_sleep(0.1)
                continue

            heart_loc, _, _ = self.find_image_match(screen, 'icon_heart.png')
            if heart_loc:
                self.add_log("【操作】 点击推荐 Buff 选项")
                self.adb_click(heart_loc[0] + int(145 * (curr_w / BASE_WIDTH)),
                               heart_loc[1] + int(144 * (curr_h / BASE_HEIGHT)))
                self.safe_sleep(0.5)
                if self.find_and_click(screen, 'btn_confirm.png'):
                    self.add_log("【操作】 点击确定选择")
                    self.force_auto_next = True
                    self.safe_sleep(1.0)
                    return
            elif self.find_image_match(screen, 'btn_confirm.png')[0]:
                self.add_log("【操作】 点击盲选默认 Buff")
                self.adb_click(int(curr_w * 0.505), int(curr_h * 0.409))
                self.safe_sleep(0.5)
                if self.find_and_click(screen, 'btn_confirm.png'):
                    self.add_log("【操作】 点击确定选择")
                    self.force_auto_next = True
                    self.safe_sleep(1.0)
                    return
            self.safe_sleep(0.1)
        self.add_log("【系统】 Buff 界面超时，返回主循环", "#e67e22")

    def handle_daily_popup(self, screen, curr_w, curr_h):
        self.update_status("处理弹窗", "#3498db")
        loc, val, rect = self.find_image_match(screen, 'icon_daily_no_prompt.png')
        if rect is None:
            return

        text_left_x, text_top_y, text_w, text_h = rect
        scale_x = curr_w / BASE_WIDTH
        circle_x = text_left_x - int(DAILY_CHECKBOX_OFFSET_X * scale_x)
        circle_y = text_top_y + (text_h // 2)

        self.add_log("【操作】 勾选 [今日不再提示]")
        self.adb_click(circle_x, circle_y)
        self.safe_sleep(0.8)

        screen = self.adb_screenshot()
        if screen is not None:
            if self.find_and_click(screen, 'btn_popup_confirm.png'):
                self.add_log("【操作】 点击 [确认] 关闭弹窗")
            elif self.find_and_click(screen, 'btn_popup_continue.png'):
                self.add_log("【操作】 点击 [继续] 关闭弹窗")
            else:
                self.add_log("【操作】 未识别到底部按钮，盲点指定位置关闭")
                fallback_x = int(1250 * (curr_w / BASE_WIDTH))
                fallback_y = int(1610 * (curr_h / BASE_HEIGHT))
                self.adb_click(fallback_x, fallback_y)

            self.safe_sleep(1.5)

    def handle_siming(self, screen, curr_w, curr_h, loc):
        self.update_status("处理司命道碑", "#e67e22")
        self.add_log("【操作】 发现司命红点，进入界面")
        self.adb_click(loc[0], loc[1])
        self.safe_sleep(1.5)

        priority_list = self.current_priority
        has_selected = False
        for opt_num in priority_list:
            if not self.is_running:
                return
            if opt_num not in SIMING_COORDS:
                continue
            screen = self.adb_screenshot()
            if screen is None:
                continue
            scale_x = curr_w / BASE_WIDTH
            scale_y = curr_h / BASE_HEIGHT
            opt_x = int(SIMING_COORDS[opt_num][0] * scale_x)
            opt_y = int(SIMING_COORDS[opt_num][1] * scale_y)
            
            crop_margin = 150 
            crop_img = screen[max(0, opt_y - crop_margin):min(curr_h, opt_y + crop_margin),
                              max(0, opt_x - crop_margin):min(curr_w, opt_x + crop_margin)]
            
            _, sold_out_val, _ = self.find_image_match(crop_img, 'icon_sold_out.png', use_gray=True)
            
            if sold_out_val < IMAGE_CONFIDENCE:
                has_selected = True
                self.update_status(f"自选残纹: {SIMING_NAMES.get(opt_num, str(opt_num))}", "#9b59b6")
                self.add_log(f"【操作】 点击残纹选项 {opt_num}")
                self.adb_click(opt_x, opt_y)
                self.safe_sleep(0.5)
                screen_confirm = self.adb_screenshot()

                if self.find_and_click(screen_confirm, 'btn_select_residue.png'):
                    self.add_log(f"【操作】 选中 [{SIMING_NAMES.get(opt_num, str(opt_num))}] 并点击 [选择残纹]")
                    
                    close_x = int(805 * (curr_w / BASE_WIDTH))
                    close_y = int(1870 * (curr_h / BASE_HEIGHT))
                    # ★ 改为等待 恭喜获得 文字并关闭
                    self.wait_and_close_popup('text_congrats.png', 2.0, close_x, close_y, action_name="司命奖励")
                    break

        if not self.is_running:
            return
        screen_back = self.adb_screenshot()
        if screen_back is not None and self.find_and_click(screen_back, 'btn_back.png'):
            if has_selected:
                self.add_log("【操作】 点击返回，退出司命界面")
            else:
                self.add_log("【操作】 发现全部选满/未开启，点击返回退出")
            self.safe_sleep(2)

    def handle_daobao(self, screen, curr_w, curr_h):
        self.update_status("处理道宝升级", "#f1c40f")
        self.add_log("【操作】 发现道宝可升级，进入界面")

        entry_loc, _ = self.find_image_safe(screen, 'daobao/entry.png', min_conf=0.8, min_bright=40)
        if not entry_loc:
            return
        
        self.adb_click(entry_loc[0], entry_loc[1])
        
        is_zaohua = False
        in_choose_screen = False
        zaohua_loc, pangu_loc = None, None
        
        for _ in range(10):
            self.safe_sleep(0.5)
            if not self.is_running:
                return
            screen = self.adb_screenshot()
            if screen is None:
                continue

            zaohua_loc, _, _ = self.find_image_match(screen, 'daobao/choose_zaohua.png')
            if zaohua_loc:
                in_choose_screen = True
                is_zaohua = True
                break
                
            pangu_loc, _, _ = self.find_image_match(screen, 'daobao/choose_pangu.png')
            if pangu_loc:
                in_choose_screen = True
                is_zaohua = False
                break
                
            cur_entry, _ = self.find_image_safe(screen, 'daobao/entry.png', min_conf=0.8, min_bright=40)
            if cur_entry:
                self.add_log("【系统】 未成功进入道宝界面，重新识别坐标并重试")
                self.adb_click(cur_entry[0], cur_entry[1])

        if not in_choose_screen:
            self.add_log("【系统】 等待道宝选择界面超时，放弃进入，返回主循环")
            return

        if is_zaohua:
            self.adb_click(zaohua_loc[0], zaohua_loc[1])
            self.add_log("【操作】 进入造化道果")
        else:
            self.adb_click(pangu_loc[0], pangu_loc[1])
            self.add_log("【操作】 进入盘古神木")
                
        self.safe_sleep(2)

        if not self.is_running:
            return
        screen = self.adb_screenshot()
        if screen is None:
            return

        prefix = "daobao/zaohua" if is_zaohua else "daobao/pangu"
        opts = [f"{prefix}_opt1.png", f"{prefix}_opt2.png", f"{prefix}_opt3.png"]

        exhausted_opts = []
        has_gray_nourish = False

        loop_count = 0
        while self.is_running and loop_count < 30:
            loop_count += 1
            if not self._wait_if_paused():
                return

            screen = self.adb_screenshot()
            if screen is None:
                break

            inside_img = f"{prefix}_inside.png"
            inside_loc, _, _ = self.find_image_match(screen, inside_img)
            if not inside_loc:
                self.add_log("【系统】 掉出道宝界面，尝试退出")
                break

            if self.find_and_click(screen, 'daobao/btn_upgrade_stage.png'):
                self.add_log("【操作】 点击升阶成功！")
                
                close_x = int(820 * (curr_w / BASE_WIDTH))
                close_y = int(2100 * (curr_h / BASE_HEIGHT))
                # ★ 改为等待 升阶成功 文字并关闭，时间根据你说的设为 4.5 秒
                self.wait_and_close_popup('text_upgrade_success.png', 4.5, close_x, close_y, action_name="升阶成功")
                
                exhausted_opts.clear()
                continue

            green_loc, green_val, _ = self.find_image_match(screen, 'daobao/btn_nourish_green.png')
            _, gray_val, _ = self.find_image_match(screen, 'daobao/btn_nourish_gray.png')

            if green_val > gray_val:
                if green_loc:
                    self.adb_click(green_loc[0], green_loc[1])
                    self.add_log("【操作】 点击滋养")
                    self.safe_sleep(0.6)

                    screen_check = self.adb_screenshot()
                    if screen_check is not None:
                        popup_loc, _ = self.find_image_safe(screen_check, 'daobao/popup_lingye.png', min_conf=0.8, min_bright=60)
                        if popup_loc:
                            self.add_log("【操作】 发现 [造化灵液] 弹窗，点击关闭")
                            close_x = int(830 * (curr_w / BASE_WIDTH))
                            close_y = int(2275 * (curr_h / BASE_HEIGHT))
                            self.wait_and_close_popup('daobao/popup_lingye.png', 2.0, close_x, close_y, action_name="造化灵液")
                            self.safe_sleep(0.5)
                    continue

            if gray_val > 0.6:
                self.add_log("【系统】 滋养按钮变灰（缺资源），无法升阶，直接退出")
                has_gray_nourish = True
                break

            clicked_opt_this_round = False
            for opt in opts:
                if not self.is_running:
                    return
                if opt in exhausted_opts:
                    continue

                loc, max_val, _ = self.find_image_match(screen, opt, use_gray=True)
                if max_val >= 0.55 and loc:
                    center_x, center_y = loc
                    self.add_log(f"【操作】 切换属性: {os.path.basename(opt)}")
                    self.adb_click(center_x, center_y)
                    self.safe_sleep(0.8)

                    screen_after = self.adb_screenshot()
                    if screen_after is not None:
                        _, g_val_after, _ = self.find_image_match(screen_after, 'daobao/btn_nourish_green.png')
                        _, gr_val_after, _ = self.find_image_match(screen_after, 'daobao/btn_nourish_gray.png')

                        if g_val_after > gr_val_after and g_val_after > 0.6:
                            pass
                        elif gr_val_after > 0.6:
                            self.add_log(f"【系统】 {os.path.basename(opt)} 资源不足（变灰），准备退出")
                            has_gray_nourish = True
                        else:
                            self.add_log(f"【系统】 {os.path.basename(opt)} 满阶（滋养消失）")
                            exhausted_opts.append(opt)
                    clicked_opt_this_round = True
                    break

            if has_gray_nourish:
                break
            if clicked_opt_this_round:
                continue

            if len(exhausted_opts) == 3:
                self.add_log("【操作】 三个属性均已满阶，尝试点开内部大图升阶")
                self.adb_click(inside_loc[0], inside_loc[1])
                self.safe_sleep(1.5)

        if not self.is_running:
            return
        self.add_log("【操作】 退出道宝界面")

        screen_back = self.adb_screenshot()
        if screen_back is not None:
            self.find_and_click(screen_back, 'btn_back.png')
            self.safe_sleep(1.5)

            screen_check = self.adb_screenshot()
            if screen_check is not None:
                if self.find_image_match(screen_check, 'daobao/choose_zaohua.png')[0] or \
                   self.find_image_match(screen_check, 'daobao/choose_pangu.png')[0]:
                    self.add_log("【系统】 仍在道宝选择界面，再次点击返回")
                    self.find_and_click(screen_check, 'btn_back.png')
                    self.safe_sleep(1.5)
                else:
                    self.add_log("【系统】 已回到主界面")

    # ------------------ 主循环 ------------------
    def automation_loop(self):
        current_port = f"127.0.0.1:{self.adb_port}"
        self.add_log(f"【系统】 正在尝试连接ADB: {current_port} ...")

        try:
            res = subprocess.run(f'"{ADB_PATH}" connect {current_port}', shell=True,
                                 capture_output=True, text=True, cwd=ADB_CWD, timeout=5)
            if "connected" in res.stdout.lower() or "already" in res.stdout.lower():
                self.add_log(f"✅ ADB 连接成功！")
            else:
                self.add_log(f"⚠️ ADB 返回信息: {res.stdout.strip()}")
        except subprocess.TimeoutExpired:
            self.add_log(f"❌ ADB 连接超时，请检查模拟器是否卡死！", "#e74c3c")
        except Exception as e:
            self.add_log(f"❌ ADB 连接异常: {e}", "#e74c3c")

        while self.is_running:
            if not self._wait_if_paused():
                break

            if not self.is_running:
                break

            screen = self.adb_screenshot()
            if screen is None:
                self.update_status("ADB未响应", "#e67e22")
                self.safe_sleep(2)
                continue
            curr_h, curr_w = screen.shape[:2]

            if self.find_image_match(screen, 'icon_daily_no_prompt.png')[0]:
                self.handle_daily_popup(screen, curr_w, curr_h)
                self.fast_track_main_ui()
                continue

            if self.find_and_click(screen, 'icon_no_reward.png'):
                self.update_status("关闭 [无奖励] 弹窗", "#e74c3c")
                close_x = int(804 * (curr_w / BASE_WIDTH))
                close_y = int(1980 * (curr_h / BASE_HEIGHT))
                self.wait_and_close_popup('icon_no_reward.png', 2.0, close_x, close_y, action_name="无奖励")
                self.force_challenge_next = True
                self.is_auto_challenging = False
                self.fast_track_main_ui()
                continue

            if self.find_and_click(screen, 'btn_claim.png'):
                self.update_status("领取奖励", "#3498db")
                self.add_log("【操作】 点击 [领取奖励] 按钮")
                close_x = int(805 * (curr_w / BASE_WIDTH))
                close_y = int(1870 * (curr_h / BASE_HEIGHT))
                # ★ 改为等待 恭喜获得 文字并关闭
                self.wait_and_close_popup('text_congrats.png', 2.0, close_x, close_y, action_name="战斗奖励")
                self.force_challenge_next = True
                self.is_auto_challenging = False
                self.fast_track_main_ui()
                continue

            if self.find_image_match(screen, 'btn_fail.png')[0]:
                self.fail_count += 1
                self.update_status("战斗失败", "#e74c3c")
                self.add_log(f"【状态】 本次关卡已连续失败 {self.fail_count} 次")
                
                close_success = False
                attempt = 1
                
                while self.is_running:
                    if not self._wait_if_paused():
                        break
                        
                    self.add_log(f"【操作】 点击上方空白关闭失败界面 (尝试 {attempt})")
                    self.adb_click(curr_w // 2, int(curr_h * 0.30))
                    self.safe_sleep(0.6) 
                    
                    check_scr = self.adb_screenshot()
                    if check_scr is not None and not self.find_image_match(check_scr, 'btn_fail.png')[0]:
                        close_success = True
                        break
                    
                    attempt += 1
                
                if close_success:
                    self.add_log("【系统】 失败界面已成功关闭")
                    self.force_challenge_next = True
                    self.is_auto_challenging = False
                    self.fast_track_main_ui()
                continue

            if self.find_and_click(screen, 'btn_win.png'):
                self.update_status("战斗胜利，点击感悟", "#2ecc71")
                self.add_log("【操作】 点击 [感悟道碑残纹]")
                if self.fail_count > 0:
                    self.add_log(f"【状态】 战斗胜利！清空失败计数 (共凹了 {self.fail_count} 次)")
                self.fail_count = 0
                self.is_auto_challenging = False
                self.check_siming_now = True

                self.safe_sleep(0.8)
                self.handle_buff_loop(curr_w, curr_h)
                continue

            # 1. ★ 司命优先查验（不受状态锁限制，只要出现了就点）
            has_siming, siming_click_loc = self.check_siming_with_dot(screen)
            if has_siming and siming_click_loc:
                self.handle_siming(screen, curr_w, curr_h, siming_click_loc)
                continue

            # 2. ★ 道宝检测
            entry_loc, _ = self.find_image_safe(screen, 'daobao/entry.png', min_conf=0.8, min_bright=40)
            if entry_loc:
                self.handle_daobao(screen, curr_w, curr_h)
                continue

            # 3. ★ 自动挑战 / 前往挑战（主界面优先推进）
            if self.force_auto_next:
                auto_loc, auto_val = self.find_image_safe(screen, 'btn_auto.png', min_conf=0.6, min_bright=40)
                if auto_loc:
                    self.adb_click(auto_loc[0], auto_loc[1])
                    self.update_status("开启自动挑战", "#2ecc71")
                    self.add_log("【操作】 点击 [自动挑战] 按钮")
                    self.force_auto_next = False
                    self.is_auto_challenging = True
                    self.safe_sleep(1.5)
                    continue
                else:
                    self.add_log(f"【等待】 自动挑战亮度/置信度不达标", "#e67e22")
                    self.safe_sleep(0.5)
                    continue

            challenge_loc, _ = self.find_image_safe(screen, 'btn_challenge.png', min_conf=0.8, min_bright=20)
            if challenge_loc:
                self.safe_sleep(0.5)
                check_screen = self.adb_screenshot()
                if check_screen is not None:
                    if self.find_image_match(check_screen, 'btn_claim.png')[0] or \
                       self.find_image_match(check_screen, 'btn_win.png')[0] or \
                       self.find_image_match(check_screen, 'icon_no_reward.png')[0]:
                        self.add_log("【系统】 发现结算按钮覆盖，暂缓点挑战", "#e67e22")
                        continue

                if self.force_challenge_next:
                    self.force_challenge_next = False
                    self.update_status("准备点击【前往挑战】", "#2ecc71")
                    self.add_log("【操作】 点击【前往挑战】")
                    self.adb_click(challenge_loc[0], challenge_loc[1])
                    self.update_status("正在等待战斗加载...", "#2ecc71")
                    # ★ 动态等待：最多等 4 秒，只要挑战按钮消失了就立刻走
                    for _ in range(8):
                        self.safe_sleep(0.5)
                        chk = self.adb_screenshot()
                        if chk is None or not self.find_image_safe(chk, 'btn_challenge.png', min_conf=0.85, min_bright=25)[0]:
                            break
                    continue

                if not self.is_auto_challenging:
                    self.update_status("准备点击【前往挑战】", "#2ecc71")
                    self.add_log("【操作】 点击【前往挑战】")
                    self.adb_click(challenge_loc[0], challenge_loc[1])
                    # ★ 动态等待：最多等 4 秒，只要挑战按钮消失了就立刻走
                    for _ in range(8):
                        self.safe_sleep(0.5)
                        chk = self.adb_screenshot()
                        if chk is None or not self.find_image_safe(chk, 'btn_challenge.png', min_conf=0.85, min_bright=25)[0]:
                            break
                    continue
                else:
                    self.is_auto_challenging = False
                    continue

            # 4. ★ 侧边残纹（用高门控拦截主界面的假图标，如果不满足前面的主界面操作，才去点它）
            side_loc, _ = self.find_image_safe(screen, 'icon_side.png', min_conf=0.75, min_bright=40)
            if side_loc:
                self.update_status("点击侧边道碑残纹", "#e67e22")
                self.add_log("【操作】 点击侧边道碑残纹图标")
                self.adb_click(side_loc[0], side_loc[1])
                self.safe_sleep(1.0)
                self.handle_buff_loop(curr_w, curr_h)
                continue

            if self.is_auto_challenging:
                self.update_status("自动挑战中...", "gray")
            else:
                self.update_status("等待画面刷新...", "gray")
            self.safe_sleep(0.1)

        self.add_log("【系统】 后台线程已安全退出。")

    def start_task(self):
        if not self.is_running:
            self.is_running = True
            self.is_paused = False
            self.current_state = ""
            self.fail_count = 0
            self.is_auto_challenging = False
            self.force_challenge_next = False
            self.force_auto_next = False
            self.check_siming_now = False
            
            self.last_action_time = time.time()
            self.alert_triggered = False

            self.start_btn.configure(state="disabled")
            self.pause_btn.configure(state="normal", text="暂停", fg_color="#f1c40f",
                                     hover_color="#f39c12", text_color="black")
            self.stop_btn.configure(state="normal")

            self.update_status("启动成功，准备扫描...", "#2ecc71")
            self.thread = threading.Thread(target=self.automation_loop, daemon=True)
            self.thread.start()
            
            threading.Thread(target=self.watchdog_thread, daemon=True).start()

    def toggle_pause(self, auto=False):
        if self.is_running:
            if not self.is_paused:
                self.is_paused = True
                self.pause_btn.configure(text="继续", fg_color="#3498db",
                                         hover_color="#2980b9", text_color="white")
                self.update_status("已暂停", "#f1c40f")
                
                if auto:
                    self.add_log("【系统】 已自动暂停脚本", "#e74c3c")
                else:
                    self.add_log("【系统】 用户点击了暂停")
            else:
                self.is_paused = False
                self.pause_btn.configure(text="暂停", fg_color="#f1c40f",
                                         hover_color="#f39c12", text_color="black")
                self.update_status("恢复运行中...", "#2ecc71")
                self.add_log("【系统】 用户点击了继续")
                
                self.last_action_time = time.time()
                self.alert_triggered = False

    def stop_task(self):
        if self.is_running:
            self.is_running = False
            self.is_paused = False
            self.start_btn.configure(state="normal")
            self.pause_btn.configure(state="disabled", text="暂停",
                                     fg_color="#f1c40f", text_color="black")
            self.stop_btn.configure(state="disabled")
            self.update_status("已停止", "#e74c3c")
            self.add_log("【系统】 用户手动停止运行。")

if __name__ == "__main__":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    app = GameAutomationApp(root)
    root.mainloop()