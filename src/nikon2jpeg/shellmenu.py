"""Per-user Windows Explorer context-menu entries (no admin rights)."""

from __future__ import annotations

import sys

if sys.platform != "win32":  # pragma: no cover
    raise ImportError("shellmenu is Windows-only")

import winreg

ROOT = r"Software\Classes"
ENTRIES = [
    # (registry key, label, argument placeholder)
    (r"Directory\shell\NikonToJpeg", "Convert NEF to JPEG", "%1"),
    (r"Directory\Background\shell\NikonToJpeg", "Convert NEF to JPEG (this folder)", "%V"),
    (r"SystemFileAssociations\.nef\shell\NikonToJpeg", "Convert to JPEG", "%1"),
]


def _launcher() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" -m nikon2jpeg'


def install() -> None:
    for key, label, arg in ENTRIES:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{ROOT}\{key}") as k:
            winreg.SetValueEx(k, "MUIVerb", 0, winreg.REG_SZ, label)
            winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, sys.executable)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{ROOT}\{key}\command") as k:
            winreg.SetValue(k, "", winreg.REG_SZ, f'{_launcher()} convert --collect --pause "{arg}"')


def uninstall() -> None:
    for key, _, _ in ENTRIES:
        for sub in (rf"{ROOT}\{key}\command", rf"{ROOT}\{key}"):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
            except FileNotFoundError:
                pass


# Windows 11 shows classic verbs only under "Show more options". Putting an empty InprocServer32
# under this CLSID makes Explorer use the classic menu everywhere (a per-user, reversible tweak).
_CLASSIC_KEY = r"Software\Classes\CLSID\{86ca1aa0-34aa-4e8b-a509-50c905bae2a2}\InprocServer32"


def set_classic_menu(enabled: bool) -> None:
    if enabled:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _CLASSIC_KEY) as k:
            winreg.SetValue(k, "", winreg.REG_SZ, "")
        return
    parent = _CLASSIC_KEY.rsplit("\\", 1)[0]
    for sub in (_CLASSIC_KEY, parent):
        try:
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
        except FileNotFoundError:
            pass
