"""Create a local Windows shortcut to pythonw; no VBS execution is required."""
from pathlib import Path
import sys
import uuid
import subprocess
from app_version import DISPLAY_NAME


def create_launcher(project=None, target=None, shortcut=None, launch_args=()):
    if sys.platform != 'win32':
        raise RuntimeError('Create this shortcut on Windows using install.bat.')
    if not isinstance(launch_args, (list, tuple)) or any(not isinstance(arg, str) or '\x00' in arg for arg in launch_args):
        raise ValueError('Shortcut arguments must be a list of strings.')
    project = Path(project or Path(__file__).resolve().parent).resolve()
    from update_installer import executable_in
    packaged = executable_in(project / 'nuvel-windows', 'windows-x64')
    target = Path(target).resolve() if target is not None else (packaged if packaged.is_file() else None)
    if target is None:
        if launch_args:
            raise ValueError('Explicit arguments require a packaged executable target.')
        target = Path(sys.executable).with_name('pythonw.exe')
        if not target.is_file():
            raise RuntimeError('pythonw.exe is missing. Repair the Python installation first.')
        arguments = '"' + str(project / 'desktop_launcher.py') + '"'
        directory = project
    else:
        arguments = subprocess.list2cmdline(launch_args)
        directory = target.parent
    shortcut = Path(shortcut) if shortcut is not None else project / (DISPLAY_NAME + '.lnk')
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
        for index, value in ((20, str(target)), (11, arguments),
                             (9, str(directory)), (7, 'Open NÜVEL Studio without a terminal')):
            checked(method(link, index, wintypes.LPCWSTR)(link, value))
        source_icon = project / 'assets/branding/app-icon.ico'
        icon = source_icon if arguments and source_icon.is_file() else target
        checked(method(link, 17, wintypes.LPCWSTR, ctypes.c_int)(link, str(icon), 0))
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
