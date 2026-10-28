# 一念逍遥·域外古路助手 (Overmortal Road Helper)

![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

基于 Python + ADB + OpenCV 图像识别实现的《一念逍遥》自动化护肝助手。

**核心机制**：通过 ADB（安卓调试桥）向模拟器发送点击指令，并在外部截取模拟器画面进行图像匹配。**完全不注入游戏内存，不修改游戏数据**，真正做到“不抢鼠标，后台无感挂机”。

---

## ✨ 核心功能

- 🚀 **后台无感挂机**：基于 ADB 实现，挂机期间鼠标完全归你控制，模拟器被遮挡也不影响运行。
- ⚔️ **智能凹关卡**：自动识别战斗失败，自动点击空白处继续挑战，直至胜利。支持统计单关卡连续失败次数。
- 🎁 **自动选 Buff**：
  - 智能识别带“爱心”的推荐选项，并自适应点击正确位置。
  - 无爱心时进行盲选兜底。
- 🏆 **司命道碑自选**：
  - 完美解决“红点误判”问题（精准识别司命专属图标）。
  - 支持 **9 种属性自定义优先级**（支持 UI 可视化和直接输入）。
  - 自动识别“已选完”状态，智能跳过并选择下一个优先属性。
  - 选完后自动返回。
- 🌳 **道宝自动升级**：
  - 识别主界面右上角红点入口，优先进入“造化道果”，其次“盘古神木”。
  - 自动点击带绿箭头的【滋养】；灰色滋养代表资源不足，自动退出不误操作。
  - 自动处理升阶确认与“造化灵液”弹窗，避免连点卡死。
- 🎯 **全能弹窗清理**：
  - 自动识别并点击“领取奖励”。
  - 自动处理“无奖励”翻车弹窗。
  - 自动勾选每日弹窗的“今日不再提示”并确认。
- 🌗 **深/浅色主题**：主界面一键切换，带淡入淡出过渡动画。
- ⏯️ **暂停 / 继续**：挂机过程中可随时暂停检查，恢复后继续执行。
- ⚡ **性能优化**：
  - 启动时将全部模板图片载入内存，避免反复读盘。
  - 分层状态机 + 失败/弹窗后的“极速追踪”通道，减少无效全屏扫描。
  - 可打断休眠，点击“停止运行”立即响应。
- 📐 **多分辨率自适应**：所有坐标与点击位置均按1660:2560等比例缩放，更换不同等比例分辨率的模拟器也能自动适配（需重新校准一次图片）。
- 💾 **配置记忆功能**：自动保存用户的 ADB 端口、优先级设置到 `config.json`，无需每次重新配置。

---

## 🛠️ 快速开始（普通用户）

### 1. 下载软件
请前往本仓库的 [Releases](https://github.com/lsw-one/overmortal-road-helper/releases) 页面，下载最新版本的 `OuterRoadHelper.zip` 或`OuterRoadHelper.7z`压缩包。

### 2. 解压与运行
- 将压缩包解压到**纯英文路径**下（例如 `D:\GameBot`，**切勿放在中文或带空格的路径下**）。
- 双击运行 `OuterRoadHelper.exe`。
- `OuterRoadHelper.exe` 必须与 `_internal` 文件夹保持在同一目录，**请勿单独移动 exe**，否则程序无法启动。

### 3. 配置模拟器
1. 打开你的安卓模拟器（支持 MuMu、雷电、夜神等），进入《一念逍遥》游戏主界面。
2. **开启 ADB 调试**：在模拟器设置中找到并开启 ADB 调试功能。
   - MuMu 12 通常为：`16384` 或 `16416`
   - 雷电通常为：`5555`
3. **对齐分辨率**：为了确保图像识别精准，请在模拟器设置中将分辨率调整为 **`1660 x 2560`**（推荐平板模式）。如果你使用其他分辨率，请确保宽高比一致。
4. 打开助手，点击右上角 **⚙️ 设置**，填入对应的 ADB 端口号，点击保存。

### 4. 开始挂机
点击主界面的 **开启后台挂机**，然后你就可以去干别的了！软件会自动接管后续操作。

---

## 💻 开发者编译指南

如果你希望自己修改源码并重新打包成 EXE，请参考以下步骤：

### 1. 环境准备
推荐使用 Anaconda 创建一个干净的 Python 3.10 环境：
```bash
conda create -n game_tool python=3.10 -y
conda activate game_tool
pip install -r requirements.txt
```

### 2. 运行源码
```bash
python auto_tool.py
```

### 3. 打包 EXE
```bash
pyinstaller OuterRoadHelper.spec --noconfirm --clean
```
- 产物为 onedir 布局，输出到 `dist/OuterRoadHelper/`，`OuterRoadHelper.exe` 必须与 `_internal` 目录一起分发。
- `OuterRoadHelper.spec` 已自动收集 conda 环境的 `Library\bin` 下的 Tcl/Tk、libffi 等运行库，并关闭了 UPX 压缩，避免 DLL 被压缩损坏。
- 若修改了代码但依赖未变，可去掉 `--clean` 加快增量打包；依赖有变化时务必加 `--clean`。

### 4. 素材目录
所有模板图片位于 `assets/images/`，按 `common` / `battle` / `buff` / `siming` / `daobao` 分类存放。代码支持**全目录递归查找**，新增素材只需放入对应文件夹并按原文件名命名，无需修改代码。素材命名规范与匹配细节见 [说明.md](说明.md)。
