# converter.spec
import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Define the name of the script
script = "converter.py"

# Only the PyQt5 submodules converter.py actually imports -- collect_submodules("PyQt5")
# pulls in every Qt module (QtQml, QtQuick, QtWebEngine, QtSql, ...) none of which this
# app uses, which bloats the build to hundreds of MB and makes PyInstaller's analysis
# extremely slow.
hidden_imports = ["PyQt5.QtWidgets", "PyQt5.QtGui", "PyQt5.QtCore"] + collect_submodules("PIL") + collect_submodules("fitz")

# NOTE: no collect_data_files("PyQt5") here -- it copies the entire PyQt5/Qt5/bin
# folder (every Qt*.dll: QtWebEngine, QtQml, QtSql, ...) regardless of hidden_imports.
# PyInstaller's own PyQt5 hook already collects exactly the plugins/DLLs needed for
# the Qt modules actually imported (QtWidgets/QtGui/QtCore).
datas = collect_data_files("PIL") + [("icon.ico", ".")]

# Define the path to the icon based on the operating system
if sys.platform == "win32":
    icon_path = os.path.abspath("icon.ico")
elif sys.platform == "darwin":
    icon_path = os.path.abspath("icon.icns")
else:
    icon_path = os.path.abspath("icon.png")

# This machine's global Python environment has heavy ML/data-science packages
# installed for unrelated projects (torch, opencv, onnxruntime, ...). None of them
# are imported by converter.py -- PyInstaller only pulls them in because PIL/fitz
# have try/except-guarded optional imports of some of these, and static analysis
# can't tell they'd never actually run. Excluding them keeps the build to what this
# app actually needs.
excludes = [
    "torch", "torchvision", "cv2", "onnxruntime", "tokenizers", "transformers",
    "hf_xet", "scipy", "numpy", "cryptography", "pandas",
]

# Define the specification
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
