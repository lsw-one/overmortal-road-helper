# -*- mode: python ; coding: utf-8 -*-

import os
import sys
# 引入 PyInstaller 的钩子工具
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# conda 环境把 Tcl/Tk、libffi 等运行库放在 Library\bin，PyInstaller 不会自动收集
_conda_binaries = []
_conda_bin = os.path.join(sys.prefix, 'Library', 'bin')
for _name in ('tcl86t.dll', 'tk86t.dll', 'ffi.dll', 'libbz2.dll', 'libexpat.dll', 'liblzma.dll'):
    _path = os.path.join(_conda_bin, _name)
    if os.path.exists(_path):
        _conda_binaries.append((_path, '.'))

# ★ 收集 customtkinter 的内部数据文件（主题 json、字体等）和所有子模块
ctk_datas = collect_data_files('customtkinter')
ctk_hiddenimports = collect_submodules('customtkinter')

a = Analysis(
    ['auto_tool.py'],
    pathex=[],
    binaries=_conda_binaries,
    datas=[
        ('assets/images', 'assets/images'), 
        ('assets/icon.ico', 'assets'), 
        ('adb', 'adb')
    ] + ctk_datas,  # ★ 合并 customtkinter 的数据文件
    hiddenimports=[
        'numpy', 
        'cv2', 
        'PIL', 
        'PIL._imaging'
    ] + ctk_hiddenimports,  # ★ 补充隐藏导入，防止运行时找不到模块
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='OuterRoadHelper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,          # ★ 建议改为 False，防止 cv2 和 tcl/tk 的 DLL 被压坏
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets/icon.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,          # ★ 同样改为 False
    upx_exclude=[],
    name='OuterRoadHelper',
)