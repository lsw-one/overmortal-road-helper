import cv2
import numpy as np
import subprocess
import os
import json
import sys

# ================= 路径配置 =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "assets", "images")
ADB_PATH = os.path.join(BASE_DIR, "adb", "adb.exe")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

# ================= 中文名称映射 =================
IMG_CN_NAMES = {
    # 1. 通用与基础类
    "btn_back.png": "返回按钮",
    "btn_popup_confirm.png": "弹窗[确认]按钮",
    "btn_popup_continue.png": "弹窗[继续]按钮",
    "icon_daily_no_prompt.png": "今日不再提示(文字)",
    
    # 2. 战斗与日常类
    "btn_challenge.png": "主界面[前往挑战]",
    "btn_fail.png": "失败界面(文字)",
    "btn_win.png": "胜利界面[感悟道碑残纹]",
    "btn_auto.png": "主界面[自动挑战]",
    "icon_heart.png": "选Buff(爱心标志)",
    "icon_side.png": "右侧[侧边残纹]",
    "btn_confirm.png": "选Buff[确定]按钮",
    "icon_no_reward.png": "无奖励弹窗(带黑底)",
    "btn_claim.png": "[领取奖励]按钮",
    
    # 3. 司命道碑类
    "btn_siming_no_dot.png": "司命道碑无红点",
    "icon_red_dot.png": "司命红点",
    "btn_select_residue.png": "[选择残纹]按钮",
    "icon_sold_out.png": "已选完(半透明字样)",
    
    # 4. 道宝升级类 - 基础
    "entry.png": "道宝可升级(入口)",
    "choose_zaohua.png": "选择界面(造化道果)",
    "choose_pangu.png": "选择界面(盘古神木)",
    "zaohua_inside.png": "造化道果内部大图",
    "pangu_inside.png": "盘古神木内部大图",
    "btn_nourish_green.png": "滋养按钮(绿/可点)",
    "btn_nourish_gray.png": "滋养按钮(灰/缺资源)",
    "btn_upgrade_stage.png": "[升阶]按钮",
    "popup_lingye.png": "造化灵液(弹窗文字)",

    # 5. 道宝升级类 - 具体属性
    "pangu_opt1.png": "盘古属性1(木灵蕴养)",
    "pangu_opt2.png": "盘古属性2(根脉固元)",
    "pangu_opt3.png": "盘古属性3(灵枝润泽)",
    "zaohua_opt1.png": "造化属性1(蕴养灵机)",
    "zaohua_opt2.png": "造化属性2(参悟道则)",
    "zaohua_opt3.png": "造化属性3(映照造化)",
}

def get_adb_port():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("adb_port", "16416")
        except Exception:
            pass
    return "16416"

def get_screenshot(port):
    if not os.path.exists(ADB_PATH):
        print(f"❌ 找不到 adb.exe，请检查路径: {ADB_PATH}")
        return None
        
    cmd = f'"{ADB_PATH}" -s 127.0.0.1:{port} exec-out screencap -p'
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, startupinfo=startupinfo, cwd=os.path.dirname(ADB_PATH), timeout=5)
        if result.returncode != 0 or not result.stdout:
            print("❌ 截图失败，请检查模拟器是否开启，或端口是否填错。")
            return None
        img_bytes = np.frombuffer(result.stdout, np.uint8)
        screen = cv2.imdecode(img_bytes, cv2.IMREAD_COLOR)
        return screen
    except Exception as e:
        print(f"❌ 截图异常: {e}")
        return None

def main():
    print("==================================================")
    print("     素材置信度 & 亮度检测工具 (无限循环版)")
    print("==================================================")

    while True:
        print("\n" + "=" * 50)
        scene_name = input("请输入当前界面的说明 (如: 主界面, 司命界面. 输入 q 退出): ").strip()
        
        if scene_name.lower() in ['q', 'quit', 'exit']:
            print("已退出测试。")
            break
            
        if not scene_name:
            scene_name = "未命名界面"

        port = get_adb_port()
        print(f"\n⏳ 正在截取屏幕 (端口: {port})...")
        screen = get_screenshot(port)
        
        if screen is None:
            input("\n按回车键重试...")
            continue

        if not os.path.exists(IMG_DIR):
            print(f"❌ 找不到图片目录: {IMG_DIR}")
            input("\n按回车键重试...")
            continue

        print(f"✅ 截图成功，分辨率: {screen.shape[1]}x{screen.shape[0]}")
        print("⏳ 正在加载素材并匹配，请稍候...\n")
        
        results = []
        
        # 遍历所有 png 图片
        for root, dirs, files in os.walk(IMG_DIR):
            for file in files:
                if file.lower().endswith(".png"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, IMG_DIR).replace("\\", "/")
                    
                    template = cv2.imdecode(np.fromfile(full_path, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if template is None:
                        continue
                        
                    h_t, w_t = template.shape[:2]
                    if h_t > screen.shape[0] or w_t > screen.shape[1]:
                        continue
                        
                    # 执行匹配
                    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    
                    # 计算匹配区域的绝对亮度
                    mean_brightness = 0
                    if max_val > 0.4:  # 只有分数有参考价值才去算亮度
                        x, y = max_loc
                        crop_img = screen[y:y+h_t, x:x+w_t]
                        if crop_img.size > 0:
                            gray_crop = cv2.cvtColor(crop_img, cv2.COLOR_BGR2GRAY)
                            mean_brightness = np.mean(gray_crop)
                    
                    results.append((rel_path, max_val, mean_brightness, max_loc))
                    
        # 按照相似度从高到低排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        print("="*85)
        print(f" 📍 当前场景: 【 {scene_name} 】")
        print("="*85)
        print(f"{'排名':<4} {'中文名称':<20} {'素材相对路径':<32} {'相似度':<8} {'平均亮度'}")
        print("-" * 85)
        
        for i, (rel_path, score, brightness, loc) in enumerate(results[:15]):
            filename = os.path.basename(rel_path)
            cn_name = IMG_CN_NAMES.get(filename, "未知素材")
            
            # 颜色代码：分数高的变绿，分数中间的变黄
            color_code = "\033[92m" if score >= 0.75 else ("\033[93m" if score >= 0.65 else "\033[0m")
                
            # 将亮度用颜色区分：如果亮度太低（<50），输出红色提示
            b_color = "\033[91m" if brightness < 50 and score > 0.6 else ""
            
            print(f"{color_code}{i+1:>2}. {cn_name:<18} [{rel_path:<28}] {score:.4f}  {b_color}{brightness:>6.1f}\033[0m")
        
        print("="*85)
        
        # 针对 btn_auto.png 的特殊提示
        for rel_path, score, brightness, loc in results:
            if "btn_auto.png" in rel_path:
                print("\n💡 【自动挑战按钮】专项诊断:")
                print(f"   当前画面匹配度: {score:.4f}")
                print(f"   当前画面平均亮度: {brightness:.1f}")
                if brightness < 50:
                    print("   👉 诊断结果: \033[91m【亮度太低】\033[0m 说明当前处于半透明遮挡界面！")
                    print("      即使匹配度很高（因为算法看透了结构），代码里也应该用亮度 < 50 来过滤它。")
                else:
                    print("   👉 诊断结果: \033[92m【亮度正常】\033[0m 说明当前在正常主界面或明亮界面。")
                break

        print("\n💡 阈值参考:")
        print("  < 0.50 : 极低（几乎不可用）")
        print("  0.50 - 0.65 : 勉强可用，但在动画/遮挡下容易出问题")
        print("  0.65 - 0.75 : 正常水平（代码默认门槛 0.65）")
        print("  > 0.75 : 极高（非常适合固定 UI，如道宝入口建议 > 0.75）")
        print("=" * 85)
        
        # 阻断并等待用户继续
        input("\n✅ 检测完毕。按回车键继续测试下一个界面...")

if __name__ == "__main__":
    main()