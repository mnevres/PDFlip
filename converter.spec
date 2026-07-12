# converter.spec
import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Define the name of the script
script = "converter.py"

# Collect all the hidden imports required for PyQt5, PIL, and fitz
hidden_imports = collect_submodules("PyQt5") + collect_submodules("PIL") + collect_submodules("fitz")

# Collect data files (for example, fonts, images, etc.)
datas = collect_data_files("PyQt5") + collect_data_files("PIL") + [("icon.ico", ".")]

# Define the path to the icon based on the operating system
if sys.platform == "win32":
    icon_path = os.path.abspath("icon.ico")
elif sys.platform == "darwin":
    icon_path = os.path.abspath("icon.icns")
else:
    icon_path = os.path.abspath("icon.png")

# Define the specification
a = Analysis(
    [script],
    pathex=["."],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

# Define the PyInstaller options
pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="PDFlip",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    icon=icon_path,
)
