"""Create a local Windows shortcut to pythonw; no VBS execution is required."""
from pathlib import Path
import sys
import uuid


def create_launcher(project=None):
    if sys.platform != 'win32':
        raise RuntimeError('Create this shortcut on Windows using install.bat.')
    project = Path(project or Path(__file__).resolve().parent).resolve()
    pythonw = Path(sys.executable).with_name('pythonw.exe')
    if not pythonw.is_file():
        raise RuntimeError('pythonw.exe is missing. Repair the Python installation first.')
    shortcut = project / 'YTDL Studio.lnk'
    # IShellLinkW + IPersistFile preserve Thai paths. WScript.Shell's Save can
    # reduce paths to ANSI on some systems. No PowerShell/WSH process is needed.
    # https://learn.microsoft.com/windows/win32/api/shobjidl_core/nn-shobjidl_core-ishelllinkw
    import ctypes
    from ctypes import wintypes

    def guid(value):
        return (ctypes.c_byte * 16).from_buffer_copy(uuid.UUID(value).bytes_le)

    def checked(result):
        if result < 0:
            raise OSError(f'Windows shortcut operation failed (HRESULT 0x{result & 0xffffffff:08X}).')

    def method(interface, index, *argtypes):
        table = ctypes.cast(interface, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        return ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, *argtypes)(table[index])

    ole = ctypes.WinDLL('ole32')
    ole.CoInitializeEx.argtypes = [ctypes.c_void_p, wintypes.DWORD]
    ole.CoInitializeEx.restype = ctypes.c_long
    ole.CoCreateInstance.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD,
                                    ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    ole.CoCreateInstance.restype = ctypes.c_long
    ole.CoUninitialize.argtypes = []
    ole.CoUninitialize.restype = None
    initialized = ole.CoInitializeEx(None, 2)
    if initialized != -2147417850:  # RPC_E_CHANGED_MODE: COM is already initialized in another mode.
        checked(initialized)
    link, persist = ctypes.c_void_p(), ctypes.c_void_p()
    try:
        checked(ole.CoCreateInstance(guid('00021401-0000-0000-C000-000000000046'), None, 1,
                                    guid('000214F9-0000-0000-C000-000000000046'), ctypes.byref(link)))
        for index, value in ((20, str(pythonw)), (11, '"' + str(project / 'desktop_launcher.py') + '"'),
                             (9, str(project)), (7, 'Open YTDL Studio without a terminal')):
            checked(method(link, index, wintypes.LPCWSTR)(link, value))
        checked(method(link, 17, wintypes.LPCWSTR, ctypes.c_int)(link, str(pythonw), 0))
        checked(method(link, 0, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p))(
            link, guid('0000010b-0000-0000-C000-000000000046'), ctypes.byref(persist)))
        checked(method(persist, 6, wintypes.LPCWSTR, wintypes.BOOL)(persist, str(shortcut), True))
    finally:
        if persist:
            method(persist, 2)(persist)
        if link:
            method(link, 2)(link)
        if initialized >= 0:
            ole.CoUninitialize()
    return shortcut


if __name__ == '__main__':
    print('Windowless launcher:', create_launcher())
