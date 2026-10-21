"""Nonblocking update service exposed to the existing native UI bridge."""
import copy
import shutil
import subprocess
import tempfile
import threading

from app_version import VERSION, REPOSITORY
from release_client import ReleaseClient, UpdateError
from update_credentials import credential
from update_installer import installed_bundle, platform_key, stage_update


class AppUpdates:
    def __init__(self):
        self.lock = threading.RLock()
        self.cancel = threading.Event()
        self.token = ''
        self.release = None
        self.plan = None
        self.stage = None
        self.state = dict(current=VERSION, repository=REPOSITORY, phase='idle', percent=0,
                          latest='', notes='', error='', authenticated=False, session_only=False,
                          packaged=installed_bundle() is not None, platform=platform_key())

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(self.state)

    def set(self, **values):
        with self.lock:
            self.state.update(values)

    def connect(self, token='', forget=False):
        with self.lock:
            if self.state['phase'] in ('checking', 'downloading', 'verifying', 'installing', 'ready'):
                return dict(error='update_busy')
            try:
                if forget:
                    credential(delete=True)
                    self.token = ''
                else:
                    token = str(token).strip()
                    # Validate before allowing an in-memory fallback for a locked OS store.
                    import re
                    if not re.fullmatch(r'[A-Za-z0-9_]{1,4096}', token):
                        return dict(error='credential_error')
                    try:
                        credential(token)
                        self.set(session_only=False)
                    except (OSError, subprocess.SubprocessError):
                        self.set(session_only=True)
                    self.token = token
                self.release = None
                self.set(authenticated=not forget, phase='idle', error='', latest='', notes='',
                         session_only=False if forget else self.state['session_only'])
                return dict(ok=True, session_only=self.state['session_only'])
            except (OSError, subprocess.SubprocessError):
                # Never relay OS commands/errors containing a credential into UI/logs.
                return dict(error='credential_error')

    def _start(self, phase, worker):
        with self.lock:
            if self.state['phase'] in ('checking', 'downloading', 'verifying', 'installing', 'ready'):
                return dict(error='update_busy')
            self.cancel.clear()
            self.set(phase=phase, error='', percent=0)
            threading.Thread(target=self._run, args=(worker,), daemon=True).start()
            return dict(ok=True)

    def _run(self, worker):
        try:
            worker()
        except UpdateError as exc:
            self.set(phase='available' if exc.code == 'cancelled' else 'error', error=exc.code)
        except Exception:
            self.set(phase='error', error='update_failed')

    def check(self):
        return self._start('checking', self._check)

    def _check(self):
        if not self.state['platform']:
            raise UpdateError('unsupported_system')
        if not self.token:
            try:
                self.token = credential()
            except (OSError, subprocess.SubprocessError):
                self.set(session_only=True)
        self.set(authenticated=bool(self.token))
        if not self.token:
            raise UpdateError('access_required')
        self.release = ReleaseClient(self.token).latest(self.state['platform'])
        if self.release:
            self.set(phase='available', latest=self.release['version'], notes=self.release['notes'])
        else:
            self.set(phase='up_to_date', latest='', notes='')

    def download(self):
        with self.lock:
            if not self.release:
                return dict(error='check_first')
            if not installed_bundle():
                return dict(error='source_build')
            return self._start('downloading', self._download)

    def _download(self):
        from pathlib import Path
        current = installed_bundle()
        self.plan = None
        try:
            stage = Path(tempfile.mkdtemp(prefix='.ytdl-update-', dir=current.parent))
        except OSError:
            raise UpdateError('install_readonly') from None
        self.stage = stage
        archive = stage / 'package.zip'
        try:
            ReleaseClient(self.token).download(self.release, archive,
                lambda percent: self.set(percent=percent), self.cancel)
            self.set(phase='verifying')
            if self.cancel.is_set():
                raise UpdateError('cancelled')
            self.plan = stage_update(current, archive, stage, self.state['platform'], self.release['version'])
            archive.unlink()
            self.set(phase='ready', percent=100)
        finally:
            if self.plan is None:
                # Only this service's explicitly created staging directory is removed.
                shutil.rmtree(stage, ignore_errors=True)

    def request_install(self):
        with self.lock:
            if self.state['phase'] != 'ready' or not self.plan:
                return dict(error='check_first')
            self.set(phase='installing')
            return dict(ok=True)
