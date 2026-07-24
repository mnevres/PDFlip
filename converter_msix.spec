# converter_msix.spec
# Onedir build (folder of files, not a self-extracting onefile exe) for MSIX
# packaging: MSIX already provides its own container/compression, and a
# onedir layout starts instantly instead of self-extracting to %TEMP% on
# every launch like the onefile build used for the Inno Setup installer.
import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

script = "converter.py"

hidden_imports = ["PyQt5.QtWidgets", "PyQt5.QtGui", "PyQt5.QtCore"] + collect_submodules("PIL") + collect_submodules("fitz")
datas = collect_data_files("PIL") + [("icon.ico", ".")]

if sys.platform == "win32":
    icon_path = os.path.abspath("icon.ico")
elif sys.platform == "darwin":
    icon_path = os.path.abspath("icon.icns")
else:
    icon_path = os.path.abspath("icon.png")

# See converter.spec for why these are excluded (unrelated ML packages this
# machine's global env happens to have installed, pulled in via optional imports).
excludes = [
    "torch", "torchvision", "cv2", "onnxruntime", "tokenizers", "transformers",
    "hf_xet", "scipy", "numpy", "cryptography", "pandas",
]

a = Analysis(
    [script],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PDFlip",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=icon_path,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PDFlip",
)
