"""Read-only WinMM inventory to notice changes behind PortMidi's cached list."""

import sys


def output_signature() -> tuple | None:
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    class Caps(ctypes.Structure):
        _fields_ = [("manufacturer", wintypes.WORD), ("product", wintypes.WORD),
                    ("version", wintypes.UINT), ("name", wintypes.WCHAR * 32),
                    ("technology", wintypes.WORD), ("voices", wintypes.WORD),
                    ("notes", wintypes.WORD), ("channels", wintypes.WORD),
                    ("support", wintypes.DWORD)]

    api = ctypes.WinDLL("winmm")
    api.midiOutGetNumDevs.restype = wintypes.UINT
    api.midiOutGetDevCapsW.argtypes = [ctypes.c_size_t, ctypes.POINTER(Caps), wintypes.UINT]
    api.midiOutGetDevCapsW.restype = wintypes.UINT
    devices = []
    for index in range(api.midiOutGetNumDevs()):
        caps = Caps()
        if api.midiOutGetDevCapsW(index, ctypes.byref(caps), ctypes.sizeof(caps)) != 0:
            raise OSError("MIDI device list changed; press Refresh")
        devices.append((caps.manufacturer, caps.product, caps.name, caps.version))
    return tuple(devices)
