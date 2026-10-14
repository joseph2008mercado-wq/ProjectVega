"""One-folder Windows build. Run through scripts/build-windows.ps1."""

import sys
from pathlib import Path
from PyInstaller.utils.win32.versioninfo import (
    FixedFileInfo, StringFileInfo, StringStruct, StringTable, VarFileInfo,
    VarStruct, VSVersionInfo,
)

root = Path(SPECPATH).parent
sys.path.insert(0, str(root / "src"))
from vega.app.identity import APP_DESCRIPTION, APP_NAME, APP_VERSION, EXECUTABLE_NAME

version_tuple = tuple(int(part) for part in APP_VERSION.split(".")) + (0,)
version = VSVersionInfo(
    ffi=FixedFileInfo(filevers=version_tuple, prodvers=version_tuple,
                      mask=0x3F, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0, 0)),
    kids=[StringFileInfo([StringTable("040904B0", [
        StringStruct("ProductName", APP_NAME),
        StringStruct("FileDescription", APP_DESCRIPTION),
        StringStruct("FileVersion", APP_VERSION),
        StringStruct("ProductVersion", APP_VERSION),
        StringStruct("InternalName", APP_NAME),
        StringStruct("OriginalFilename", EXECUTABLE_NAME),
    ])]), VarFileInfo([VarStruct("Translation", [1033, 1200])])],
)
icon = root / "src" / "vega" / "app" / "resources" / "vega.ico"
a = Analysis(
    [str(root / "packaging" / "windows-entry.py")],
    pathex=[str(root / "src")],
    datas=[(str(icon), "vega/app/resources")],
    hiddenimports=["mido.backends.rtmidi", "pygame.midi"],
    excludes=["pytest", "unittest", "pygame.tests", "pygame.examples", "tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=APP_NAME,
          console=False, icon=str(icon), version=version, upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name=APP_NAME, upx=False)
