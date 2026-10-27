import tkinter as tk
import tkinter.messagebox
from tkinter import scrolledtext
import subprocess
import cv2
import numpy as np
import threading
import time
import os
import sys
import json
import webbrowser

# ================= 配置区域 =================
IMAGE_CONFIDENCE = 0.65       
LOOP_DELAY = 0.1              
BASE_WIDTH = 1660
BASE_HEIGHT = 2560
CONFIG_FILE = "config.json"

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

# 自适应 ADB 路径并返回其所在的目录作为工作目录
if os.path.exists(os.path.join(BASE_DIR, "adb", "adb.exe")):
    ADB_PATH = os.path.join(BASE_DIR, "adb", "adb.exe")
    ADB_CWD = os.path.join(BASE_DIR, "adb")
elif os.path.exists(os.path.join(BASE_DIR, "adb.exe")):
    ADB_PATH = os.path.join(BASE_DIR, "adb.exe")
    ADB_CWD = BASE_DIR
else:
    ADB_PATH = os.path.join(BASE_DIR, "adb", "adb.exe") # 兜底
    ADB_CWD = BASE_DIR

# 自适应图片路径
if os.path.exists(os.path.join(BASE_DIR, "assets", "images")):
    IMG_DIR = os.path.join(BASE_DIR, "assets", "images")
else:
    IMG_DIR = os.path.join(BASE_DIR, "images")

CONFIG_PATH = os.path.join(APP_DIR, CONFIG_FILE)

def get_img_path(filename):
    return os.path.join(IMG_DIR, filename)

# ================= 设置窗口类 =================
class SettingsWindow(tk.Toplevel):
    def __init__(self, master, main_app):
        super().__init__(master)
        self.main_app = main_app
        self.title("域外古路助手 - 设置")
        self.geometry("520x760") 
        self.resizable(False, False)
        self.transient(master) 
        self.grab_set()        

        dev_frame = tk.LabelFrame(self, text=" 模拟器连接设置 ", font=("微软雅黑", 10, "bold"))
        dev_frame.pack(fill="x", padx=20, pady=10)
        
        tk.Label(dev_frame, text="ADB 端口:", font=("微软雅黑", 10)).grid(row=0, column=0, padx=5, pady=5)
        self.port_entry = tk.Entry(dev_frame, width=10, font=("微软雅黑", 10), justify="center")
        self.port_entry.insert(0, main_app.adb_port)
        self.port_entry.grid(row=0, column=1, padx=5)
        tk.Label(dev_frame, text="(MuMu 通常为 16384 或 16416)", fg="gray", font=("微软雅黑", 8)).grid(row=0, column=2, padx=5)

        tk.Label(self, text="【司命道碑】优先级设置", font=("微软雅黑", 11, "bold")).pack(pady=(10, 0))
        input_frame = tk.Frame(self)
        input_frame.pack(pady=5)
        
        self.entry_var = tk.StringVar(value=",".join(str(x) for x in main_app.current_priority))
        self.priority_entry = tk.Entry(input_frame, textvariable=self.entry_var, width=30, justify="center", font=("微软雅黑", 11), bg="#f0f0f0")
        self.priority_entry.pack(side=tk.LEFT, padx=5)
        
        sync_btn = tk.Button(input_frame, text="应用输入", command=self.sync_from_entry, bg="#e0e0e0", font=("微软雅黑", 9))
        sync_btn.pack(side=tk.LEFT, padx=5)

        help_frame = tk.Frame(self, bg="#f9f9f9", bd=1, relief="solid")
        help_frame.pack(pady=5, fill="x", padx=20)
        tk.Label(help_frame, text="属性编号参照", bg="#f9f9f9", fg="#333333", font=("微软雅黑", 9, "bold")).pack(pady=2)
        grid_frame = tk.Frame(help_frame, bg="#f9f9f9")
        grid_frame.pack(padx=5, pady=(0, 5))
        items = [
            "1:气血/真元", "2:物攻/法攻", "3:物防/法防",
            "4:会心/倍率", "5:会心抗性", "6:怪物增伤",
            "7:神通增伤", "8:法宝增伤", "9:古宝增伤"
        ]
        for index, text in enumerate(items):
            tk.Label(grid_frame, text=text, bg="#f9f9f9", fg="#555555", font=("微软雅黑", 9), width=12, anchor="w").grid(row=index//3, column=index%3, padx=2, pady=2)

        tk.Label(self, text="当前执行顺序 (点击箭头调整)", font=("微软雅黑", 10, "bold"), anchor="w").pack(fill="x", padx=20, pady=(5, 0))
        self.list_frame = tk.Frame(self, bg="#f0f0f0", bd=1, relief="solid")
        self.list_frame.pack(fill="x", padx=20, pady=5)
        self.render_priority_list()

        tk.Button(self, text="保存并关闭", command=self.save_and_close, bg="#90ee90", font=("微软雅黑", 11, "bold"), width=15).pack(pady=10)

        info_frame = tk.Frame(self, bg="#f0f0f0", bd=1, relief="solid")
        info_frame.pack(fill="x", side=tk.BOTTOM, padx=20, pady=(0, 15))
        
        author_label = tk.Label(info_frame, text="作者: lsw-one | GitHub: overmortal-road-helper", font=("微软雅黑", 9, "underline"), fg="blue", bg="#f0f0f0", cursor="hand2")
        author_label.pack(pady=(5, 2))
        author_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/lsw-one/overmortal-road-helper"))
        
        disclaimer_text = "免责声明：\n本软件仅供学习交流与个人护肝使用，严禁用于任何商业盈利用途。\n使用本软件产生的一切后果（包括但不限于游戏账号被封禁等）由使用者自行承担。"
        tk.Label(info_frame, text=disclaimer_text, font=("微软雅黑", 8), fg="#666666", bg="#f0f0f0", justify="center").pack(pady=(0, 5))

    def sync_from_entry(self):
        try:
            raw_text = self.entry_var.get()
            nums = [int(x.strip()) for x in raw_text.replace("，", ",").split(",") if x.strip().isdigit()]
            valid_nums = [n for n in nums if 1 <= n <= 9]
            for i in range(1, 10):
                if i not in valid_nums: valid_nums.append(i)
            self.main_app.current_priority = valid_nums[:9] 
            self.render_priority_list()
        except Exception:
            messagebox.showerror("错误", "输入格式有误，请用逗号分隔数字(1-9)", parent=self)

    def update_entry_from_list(self):
        self.entry_var.set(",".join(str(x) for x in self.main_app.current_priority))

    def render_priority_list(self):
        for widget in self.list_frame.winfo_children(): widget.destroy()
        for i, num in enumerate(self.main_app.current_priority):
            row, col = i % 5, i // 5
            row_frame = tk.Frame(self.list_frame, bg="#f0f0f0")
            row_frame.grid(row=row, column=col, padx=20, pady=2, sticky="w")
            name = SIMING_NAMES.get(num, "未知")
            tk.Label(row_frame, text=f"{i+1}. {name}", bg="#f0f0f0", font=("微软雅黑", 10, "bold"), width=14, anchor="w").pack(side=tk.LEFT)
            
            up_btn = tk.Button(row_frame, text="▲", font=("Arial", 8), width=3, command=lambda idx=i: self.move_item(idx, -1))
            up_btn.pack(side=tk.LEFT, padx=2)
            if i == 0: up_btn.config(state=tk.DISABLED)
            
            down_btn = tk.Button(row_frame, text="▼", font=("Arial", 8), width=3, command=lambda idx=i: self.move_item(idx, 1))
            down_btn.pack(side=tk.LEFT, padx=2)
            if i == len(self.main_app.current_priority) - 1: down_btn.config(state=tk.DISABLED)

    def move_item(self, index, direction):
        new_index = index + direction
        if 0 <= new_index < len(self.main_app.current_priority):
            self.main_app.current_priority[index], self.main_app.current_priority[new_index] = self.main_app.current_priority[new_index], self.main_app.current_priority[index]
            self.render_priority_list()
            self.update_entry_from_list()

    def save_and_close(self):
        self.main_app.adb_port = self.port_entry.get().strip()
        config_data = {
            "adb_port": self.main_app.adb_port,
            "priority_list": self.main_app.current_priority
        }
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
            self.main_app.add_log("设置已保存到 config.json")
        except Exception as e:
            messagebox.showerror("保存失败", f"无法保存配置文件：{e}", parent=self)

        self.destroy()


# ================= 主界面类 =================
class GameAutomationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("一念逍遥·域外古路助手 v1.1") 
        self.root.geometry("520x600") 
        self.root.configure(padx=10, pady=10) 
        
        try:
            icon_path = os.path.join(BASE_DIR, "assets", "icon.ico")
            if not os.path.exists(icon_path):
                icon_path = os.path.join(BASE_DIR, "icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception as e:
            print(f"图标加载失败: {e}")

        self.is_running = False
        self.thread = None
        self.force_auto_next = False      
        self.force_challenge_next = False 
        self.last_click_time = 0
        self.last_click_pos = (0, 0)
        self.current_state = "" 
        self.fail_count = 0
        
        self.adb_port = "16416"
        self.current_priority = [4, 2, 6, 1, 5, 8, 7, 9, 3]

        self.load_config()

        top_frame = tk.Frame(root)
        top_frame.pack(fill="x", pady=(0, 10))
        
        tk.Label(top_frame, text="域外古路助手", font=("微软雅黑", 14, "bold")).pack(side=tk.LEFT, padx=5)
        set_btn = tk.Button(top_frame, text="⚙️ 设置", command=self.open_settings, font=("微软雅黑", 10), bg="#e0e0e0")
        set_btn.pack(side=tk.RIGHT, padx=5)

        control_frame = tk.Frame(root)
        control_frame.pack(pady=10)
        
        self.status_label = tk.Label(control_frame, text="状态：未启动", fg="red", font=("微软雅黑", 14, "bold"))
        self.status_label.pack(pady=10)
        
        btn_frame = tk.Frame(control_frame)
        btn_frame.pack()
        
        self.start_btn = tk.Button(btn_frame, text="开启后台挂机", command=self.start_task, bg="#90ee90", fg="black", font=("微软雅黑", 12, "bold"), width=15)
        self.start_btn.pack(side=tk.LEFT, padx=15)
        
        self.stop_btn = tk.Button(btn_frame, text="停止运行", command=self.stop_task, bg="#ffb6c1", fg="black", font=("微软雅黑", 12, "bold"), width=15, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.RIGHT, padx=15)

        tk.Label(root, text="操作日志", font=("微软雅黑", 10, "bold"), anchor="w").pack(fill="x", padx=20, pady=(10, 0))
        self.log_text = scrolledtext.ScrolledText(root, height=18, font=("Consolas", 9), state=tk.DISABLED, bg="#1e1e1e", fg="#d4d4d4")
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=(5, 10))

        # 软件启动时进行路径体检
        self.root.after(500, self.check_files)
    
    def check_files(self):
        """启动时检查必要文件是否存在"""
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
                    self.adb_port = data.get("adb_port", "16416")
                    priority = data.get("priority_list", [4, 2, 6, 1, 5, 8, 7, 9, 3])
                    if isinstance(priority, list) and len(priority) == 9:
                        self.current_priority = priority
            except Exception as e:
                print(f"读取配置失败: {e}")

    def open_settings(self):
        for child in self.root.winfo_children():
            if isinstance(child, SettingsWindow):
                child.focus_set()
                return
        SettingsWindow(self.root, self)

    def add_log(self, msg):
        self.root.after(0, self._append_log, msg)

    def _append_log(self, msg):
        current_time = time.strftime("%H:%M:%S")
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{current_time}] {msg}\n")
        if float(self.log_text.index('end-1c').split('.')[0]) > 100:
            self.log_text.delete('1.0', '2.0')
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def update_status(self, text, color):
        self.root.after(0, self._update_status_ui, text, color)
        if text != self.current_state and "扫描中" not in text:
            self.add_log(f"【状态】 {text}")
        self.current_state = text

    def _update_status_ui(self, text, color):
        if self.is_running or "停止" in text:
            self.status_label.config(text=f"状态：{text}", fg=color)

    def adb_screenshot(self):
        current_port = f"127.0.0.1:{self.adb_port}"
        cmd = f'"{ADB_PATH}" -s {current_port} exec-out screencap -p'
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, startupinfo=startupinfo, cwd=ADB_CWD, timeout=3)
            if result.returncode != 0 or not result.stdout: return None
            img_bytes = np.frombuffer(result.stdout, np.uint8)
            return cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
        except Exception as e:
            print(f"截图异常: {e}")
            return None

    def adb_click(self, x, y):
        current_time = time.time()
        if abs(x - self.last_click_pos[0]) < 10 and abs(y - self.last_click_pos[1]) < 10:
            if current_time - self.last_click_time < 0.5: return
        self.last_click_pos = (x, y)
        self.last_click_time = current_time

        current_port = f"127.0.0.1:{self.adb_port}"
        cmd = f'"{ADB_PATH}" -s {current_port} shell input tap {x} {y}'
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo, cwd=ADB_CWD)

    def find_image_match(self, screen_img, img_name, use_gray=False):
        full_path = get_img_path(img_name)
        if not os.path.exists(full_path) or screen_img is None: return None, 0, None
        template = cv2.imdecode(np.fromfile(full_path, dtype=np.uint8), cv2.IMREAD_COLOR)
        if template is None: return None, 0, None
        if use_gray:
            screen_img = cv2.cvtColor(screen_img, cv2.COLOR_BGR2GRAY)
            template = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(screen_img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        if max_val >= IMAGE_CONFIDENCE:
            h, w = template.shape[:2]
            return (max_loc[0] + w // 2, max_loc[1] + h // 2), max_val, (max_loc[0], max_loc[1], w, h)
        return None, max_val, None

    def check_siming_with_dot(self, screen):
        loc, val, rect = self.find_image_match(screen, 'btn_siming_no_dot.png')
        if rect is None: return False, None
        base_x, base_y, w, h = rect
        dot_region = screen[max(0, base_y - 30):min(screen.shape[0], base_y + 60), max(0, base_x + w - 60):min(screen.shape[1], base_x + w + 40)]
        dot_loc, dot_val, _ = self.find_image_match(dot_region, 'icon_red_dot.png')
        if dot_loc: return True, (base_x + w // 2, base_y + h // 2)
        return False, None

    def find_and_click(self, screen_img, img_name):
        loc, _, _ = self.find_image_match(screen_img, img_name)
        if loc: self.adb_click(loc[0], loc[1]); return True
        return False

    def click_challenge(self, x, y):
        self.update_status("准备点击【前往挑战】", "green")
        self.adb_click(x, y)
        self.update_status("正在等待战斗加载...", "green")
        time.sleep(2.5)

    def handle_daily_popup(self, screen, curr_w, curr_h):
        self.update_status("处理弹窗", "#008080")
        
        loc, val, rect = self.find_image_match(screen, 'icon_daily_no_prompt.png')
        if rect is None: return
        
        text_left_x, text_top_y, text_w, text_h = rect
        scale_x = curr_w / BASE_WIDTH
        circle_x = text_left_x - int(DAILY_CHECKBOX_OFFSET_X * scale_x)
        circle_y = text_top_y + (text_h // 2)
        
        self.add_log("勾选 [今日不再提示]")
        self.adb_click(circle_x, circle_y)
        time.sleep(0.8) 
        
        screen = self.adb_screenshot() 
        if screen is not None:
            if self.find_and_click(screen, 'btn_popup_confirm.png'):
                self.add_log("点击 [确认] 关闭弹窗")
            elif self.find_and_click(screen, 'btn_popup_continue.png'):
                self.add_log("点击 [继续] 关闭弹窗")
            else:
                self.add_log("未识别到底部按钮，盲点指定位置关闭", "orange")
                fallback_x = int(1250 * (curr_w / BASE_WIDTH))
                fallback_y = int(1610 * (curr_h / BASE_HEIGHT))
                self.adb_click(fallback_x, fallback_y)
            
            time.sleep(1.5) 

    def handle_siming(self, screen, curr_w, curr_h, loc):
        self.update_status("处理司命道碑", "#d2691e")
        self.add_log("发现司命红点，进入界面")
        self.adb_click(loc[0], loc[1])
        time.sleep(1.5)

        priority_list = self.current_priority
        has_selected = False 
        for opt_num in priority_list:
            if opt_num not in SIMING_COORDS: continue
            screen = self.adb_screenshot()
            if screen is None: continue
            scale_x = curr_w / BASE_WIDTH
            scale_y = curr_h / BASE_HEIGHT
            opt_x = int(SIMING_COORDS[opt_num][0] * scale_x)
            opt_y = int(SIMING_COORDS[opt_num][1] * scale_y)
            crop_margin = 150
            crop_img = screen[max(0, opt_y - crop_margin):min(curr_h, opt_y + crop_margin), max(0, opt_x - crop_margin):min(curr_w, opt_x + crop_margin)]
            _, sold_out_val, _ = self.find_image_match(crop_img, 'icon_sold_out.png', use_gray=True)
            if sold_out_val < IMAGE_CONFIDENCE:
                has_selected = True
                self.update_status(f"自选残纹: {SIMING_NAMES.get(opt_num, str(opt_num))}", "#8a2be2")
                self.adb_click(opt_x, opt_y)
                time.sleep(0.5)
                screen_confirm = self.adb_screenshot()
                
                # 【修改点】点击“选择残纹”后，弹出奖励弹窗，盲点 (805, 1870) 关闭
                if self.find_and_click(screen_confirm, 'btn_select_residue.png'):
                    self.add_log(f"选中 [{SIMING_NAMES.get(opt_num, str(opt_num))}] 并点击确定")
                    time.sleep(1.5) # 等待奖励弹窗出现
                    
                    close_x = int(805 * (curr_w / BASE_WIDTH))
                    close_y = int(1870 * (curr_h / BASE_HEIGHT))
                    self.adb_click(close_x, close_y)
                    
                    time.sleep(1.5) # 等待弹窗关闭
                    break 

        # 最后点击返回按钮
        screen_back = self.adb_screenshot()
        if screen_back is not None and self.find_and_click(screen_back, 'btn_back.png'):
            if has_selected: self.add_log("点击返回，退出司命界面")
            else: self.add_log("发现全部选满/未开启，点击返回退出")
            time.sleep(2)

    def automation_loop(self):
        current_port = f"127.0.0.1:{self.adb_port}"
        self.add_log(f"后台线程已启动，正在连接 ADB: {current_port} ...")
        subprocess.run(f'"{ADB_PATH}" connect {current_port}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=subprocess.STARTUPINFO(), cwd=ADB_CWD)
        
        while self.is_running:
            if not self.is_running: break
            screen = self.adb_screenshot()
            if screen is None:
                self.update_status("ADB未响应，请检查端口", "orange")
                time.sleep(2)
                continue
            self.update_status("扫描中...", "green")
            curr_h, curr_w = screen.shape[:2]

            if self.find_image_match(screen, 'icon_daily_no_prompt.png')[0]:
                self.handle_daily_popup(screen, curr_w, curr_h); continue

            has_siming, siming_click_loc = self.check_siming_with_dot(screen)
            if has_siming and siming_click_loc:
                self.handle_siming(screen, curr_w, curr_h, siming_click_loc); continue

            if self.find_and_click(screen, 'icon_no_reward.png'):
                self.update_status("关闭 [无奖励] 弹窗", "red")
                close_x = int(804 * (curr_w / BASE_WIDTH))
                close_y = int(1980 * (curr_h / BASE_HEIGHT))
                self.adb_click(close_x, close_y)
                self.force_challenge_next = True; time.sleep(1); continue

            if self.click_image_claim(screen, curr_w, curr_h):
                self.force_challenge_next = True; continue

            heart_loc, _, _ = self.find_image_match(screen, 'icon_heart.png')
            if heart_loc:
                self.update_status("选择推荐 Buff", "#8a2be2")
                self.adb_click(heart_loc[0] + int(145 * (curr_w / BASE_WIDTH)), heart_loc[1] + int(144 * (curr_h / BASE_HEIGHT)))
                time.sleep(0.5)
                if self.find_and_click(screen, 'btn_confirm.png'):
                    self.add_log("点击确定选择"); self.force_auto_next = True
                time.sleep(1); continue
            elif self.find_image_match(screen, 'btn_confirm.png')[0]:
                self.update_status("盲选默认 Buff", "#8a2be2")
                self.adb_click(int(curr_w * 0.505), int(curr_h * 0.409))
                time.sleep(0.5)
                if self.find_and_click(screen, 'btn_confirm.png'):
                    self.add_log("点击确定选择"); self.force_auto_next = True
                time.sleep(1); continue

            if self.find_image_match(screen, 'btn_fail.png')[0]:
                self.fail_count += 1
                self.update_status("战斗失败，关闭弹窗", "red")
                self.add_log(f"本次关卡已连续失败 {self.fail_count} 次")
                self.adb_click(curr_w // 2, int(curr_h * 0.30))
                self.force_challenge_next = True; time.sleep(1); continue

            if self.find_and_click(screen, 'btn_win.png'):
                self.update_status("战斗胜利，点击感悟", "green")
                if self.fail_count > 0: self.add_log(f"战斗胜利！清空失败计数 (共凹了 {self.fail_count} 次)")
                self.fail_count = 0; time.sleep(1); continue

            if self.find_and_click(screen, 'icon_side.png'):
                self.update_status("点击侧边道碑残纹", "#d2691e"); time.sleep(1); continue

            challenge_loc, _, _ = self.find_image_match(screen, 'btn_challenge.png')
            if challenge_loc:
                if self.force_challenge_next:
                    self.force_challenge_next = False; self.click_challenge(challenge_loc[0], challenge_loc[1]); continue
                if self.force_auto_next:
                    if self.find_and_click(screen, 'btn_auto.png'):
                        self.update_status("开启自动挑战", "green"); self.add_log("已点击自动挑战按钮")
                        self.force_auto_next = False; time.sleep(2); continue
                    else:
                        self.force_auto_next = False; self.click_challenge(challenge_loc[0], challenge_loc[1]); continue
                self.click_challenge(challenge_loc[0], challenge_loc[1]); continue
            time.sleep(LOOP_DELAY)
        self.add_log("后台线程已安全退出。")

    def click_image_claim(self, screen, curr_w, curr_h):
        loc, _, _ = self.find_image_match(screen, 'btn_claim.png')
        if loc:
            self.update_status("点击 [领取奖励]", "blue")
            self.adb_click(loc[0], loc[1]); time.sleep(1.5) 
            self.adb_click(int(REWARD_CLOSE_POS[0] * (curr_w / BASE_WIDTH)), int(REWARD_CLOSE_POS[1] * (curr_h / BASE_HEIGHT)))
            self.add_log("领取完毕，关闭奖励弹窗"); time.sleep(1); return True
        return False

    def start_task(self):
        if not self.is_running:
            self.is_running = True; self.current_state = ""; self.fail_count = 0 
            self.start_btn.config(state=tk.DISABLED); self.stop_btn.config(state=tk.NORMAL)
            self.update_status("启动成功，准备扫描...", "green")
            self.thread = threading.Thread(target=self.automation_loop, daemon=True); self.thread.start()

    def stop_task(self):
        if self.is_running:
            self.is_running = False
            self.start_btn.config(state=tk.NORMAL); self.stop_btn.config(state=tk.DISABLED)
            self.status_label.config(text="状态：已停止", fg="red")
            self.add_log("用户手动停止运行。")

if __name__ == "__main__":
    root = tk.Tk()
    app = GameAutomationApp(root)
    root.mainloop()