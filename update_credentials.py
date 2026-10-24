"""Private-release credentials. Never use preferences, plans or browser storage."""
import ctypes
from ctypes import wintypes
import shlex
import re
import subprocess
import sys

SERVICE = 'NuvelStudio.GitHubReleases'
ACCOUNT = 'github.com'


class Credential(ctypes.Structure):
    _fields_ = [('Flags', wintypes.DWORD), ('Type', wintypes.DWORD),
                ('TargetName', wintypes.LPWSTR), ('Comment', wintypes.LPWSTR),
                ('LastWritten', wintypes.FILETIME), ('CredentialBlobSize', wintypes.DWORD),
                ('CredentialBlob', ctypes.POINTER(ctypes.c_ubyte)), ('Persist', wintypes.DWORD),
                ('AttributeCount', wintypes.DWORD), ('Attributes', ctypes.c_void_p),
                ('TargetAlias', wintypes.LPWSTR), ('UserName', wintypes.LPWSTR)]


def windows_token(value=None, delete=False):
    api = ctypes.WinDLL('advapi32', use_last_error=True)
    pointer = ctypes.POINTER(Credential)
    api.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(pointer)]
    api.CredReadW.restype = wintypes.BOOL
    api.CredWriteW.argtypes = [pointer, wintypes.DWORD]
    api.CredWriteW.restype = wintypes.BOOL
    api.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    api.CredDeleteW.restype = wintypes.BOOL
    api.CredFree.argtypes = [ctypes.c_void_p]
    if delete:
        if not api.CredDeleteW(SERVICE, 1, 0) and ctypes.get_last_error() != 1168:
            raise OSError('Could not remove the GitHub credential.')
    elif value is not None:
        blob = (ctypes.c_ubyte * len(value.encode()))(*value.encode())
        credential = Credential(Type=1, TargetName=SERVICE, UserName=ACCOUNT,
                                CredentialBlobSize=len(blob), CredentialBlob=blob, Persist=2)
        if not api.CredWriteW(ctypes.byref(credential), 0):
            raise OSError(ctypes.get_last_error(), 'Could not save to Windows Credential Manager.')
    else:
        credential = pointer()
        if not api.CredReadW(SERVICE, 1, 0, ctypes.byref(credential)):
            if ctypes.get_last_error() == 1168:
                return ''
            raise OSError('Could not read Windows Credential Manager.')
        try:
            return ctypes.string_at(credential.contents.CredentialBlob,
                                    credential.contents.CredentialBlobSize).decode()
        finally:
            api.CredFree(credential)
    return ''


def mac_token(value=None, delete=False):
    if value is not None:
        # security's interactive parser receives the secret on stdin, not argv.
        command = 'add-generic-password -U -a {} -s {} -w {}\n'.format(
            shlex.quote(ACCOUNT), shlex.quote(SERVICE), shlex.quote(value))
        result = subprocess.run(['/usr/bin/security', '-i'], input=command, text=True,
                                capture_output=True, timeout=30)
    else:
        operation = 'delete-generic-password' if delete else 'find-generic-password'
        command = ['/usr/bin/security', operation, '-a', ACCOUNT, '-s', SERVICE]
        if not delete:
            command.append('-w')
        result = subprocess.run(command, text=True, capture_output=True, timeout=30)
    if result.returncode:
        if result.returncode == 44 and value is None:
            return ''
        raise OSError('Could not access macOS Keychain.')
    return result.stdout.strip() if value is None and not delete else ''


def credential(value=None, delete=False):
    if value is not None and (not value or len(value) > 4096 or not re.fullmatch(r'[A-Za-z0-9_]+', value)):
        raise ValueError('Invalid GitHub token.')
    if sys.platform == 'win32':
        return windows_token(value, delete)
    if sys.platform == 'darwin':
        return mac_token(value, delete)
    raise OSError('Secure release credentials are supported on Windows and macOS.')
