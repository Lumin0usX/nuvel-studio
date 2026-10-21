"""Read one private GitHub release; credentials never follow asset redirects."""
import hashlib
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from app_version import REPOSITORY, VERSION, version_tuple

MAX_PACKAGE = 2 * 1024**3
ASSETS = {'windows-x64': 'YTDL-Studio-Windows-x64.zip', 'macos-arm64': 'YTDL-Studio-macOS-arm64.zip'}
MANIFEST = 'studio-update.json'


class UpdateError(RuntimeError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


class ReleaseRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        host = parsed.hostname or ''
        if parsed.scheme != 'https' or parsed.username or parsed.password or parsed.port not in (None, 443) or not (
                host == 'github.com' or host == 'api.github.com' or
                host.endswith('.githubusercontent.com')):
            raise UpdateError('invalid_release')
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected and host != 'api.github.com':
            redirected.remove_header('Authorization')
        return redirected


class ReleaseClient:
    def __init__(self, token):
        self.token = token
        self.opener = build_opener(ReleaseRedirect())

    def open(self, path, binary=False):
        # Only API paths are accepted; never authenticate a URL from release text.
        prefix = '/repos/' + REPOSITORY + '/releases/'
        if path != prefix.rstrip('/') + '?per_page=20' and (not path.startswith(prefix) or '?' in path or '..' in path):
            raise UpdateError('invalid_release')
        headers = {'Accept': 'application/octet-stream' if binary else 'application/vnd.github+json',
                   'User-Agent': 'YTDL-Studio/' + VERSION, 'X-GitHub-Api-Version': '2022-11-28'}
        if self.token:
            headers['Authorization'] = 'Bearer ' + self.token
        try:
            return self.opener.open(Request('https://api.github.com' + path, headers=headers), timeout=30)
        except HTTPError as exc:
            if exc.code in (401, 403, 404):
                raise UpdateError('access_required') from None
            raise UpdateError('network_error') from None
        except (URLError, OSError, TimeoutError):
            raise UpdateError('network_error') from None

    def json(self, path, binary=False):
        with self.open(path, binary) as response:
            data = response.read(1024 * 1024 + 1)
        if len(data) > 1024 * 1024:
            raise UpdateError('invalid_release')
        try:
            return json.loads(data)
        except (ValueError, UnicodeError):
            raise UpdateError('invalid_release') from None

    def latest(self, platform_key):
        # An empty list is different from a private repository we cannot access.
        prefix = '/repos/' + REPOSITORY + '/releases/'
        releases = self.json(prefix.rstrip('/') + '?per_page=20')
        if not isinstance(releases, list):
            raise UpdateError('invalid_release')
        stable = []
        for release in releases:
            try:
                if not release.get('draft') and not release.get('prerelease'):
                    stable.append((version_tuple(release['tag_name']), release))
            except (KeyError, ValueError, TypeError, AttributeError):
                continue
        if not stable:
            raise UpdateError('no_release')
        return self.resolve(max(stable, key=lambda item: item[0])[1], platform_key)

    def resolve(self, release, platform_key):
        try:
            tag = release['tag_name']
            latest = version_tuple(tag)
            if release.get('draft') or release.get('prerelease'):
                raise ValueError()
            if latest <= version_tuple(VERSION):
                return None
            assets = {item['name']: item for item in release['assets'] if item.get('state') == 'uploaded'}
            manifest = self.json(self.asset_path(assets[MANIFEST]), binary=True)
            if manifest['schema'] != 1 or manifest['version'] != tag.removeprefix('v'):
                raise ValueError()
            item = manifest['platforms'][platform_key]
            if item['name'] != ASSETS[platform_key] or not re.fullmatch(r'[a-f0-9]{64}', item['sha256']):
                raise ValueError()
            asset = assets[item['name']]
            size = item['size']
            if type(size) is not int or not 0 < size <= MAX_PACKAGE or size != asset['size']:
                raise ValueError()
            return dict(version=manifest['version'], notes=str(release.get('body') or '')[:16000],
                        name=item['name'], sha256=item['sha256'], size=size, path=self.asset_path(asset))
        except (KeyError, ValueError, TypeError):
            raise UpdateError('invalid_release') from None

    @staticmethod
    def asset_path(asset):
        if type(asset.get('id')) is not int or asset['id'] <= 0:
            raise UpdateError('invalid_release')
        return '/repos/' + REPOSITORY + '/releases/assets/' + str(asset['id'])

    def download(self, release, destination, progress, cancelled):
        digest, count = hashlib.sha256(), 0
        try:
            with self.open(release['path'], True) as response, destination.open('xb') as output:
                while True:
                    if cancelled.is_set():
                        raise UpdateError('cancelled')
                    data = response.read(1024 * 256)
                    if not data:
                        break
                    count += len(data)
                    if count > release['size']:
                        raise UpdateError('invalid_package')
                    output.write(data)
                    digest.update(data)
                    progress(round(count * 100 / release['size']))
            if count != release['size'] or digest.hexdigest() != release['sha256']:
                raise UpdateError('invalid_package')
        except BaseException:
            destination.unlink(missing_ok=True)
            raise
