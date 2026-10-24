"""Application version, independent of the download-engine version."""
VERSION = '2.0.0'
DISPLAY_NAME = 'NÜVEL Studio'
REPOSITORY = 'Lumin0usX/nuvel-studio'


def version_tuple(value):
    import re
    match = re.fullmatch(r'v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', value)
    if not match:
        raise ValueError('A stable version must use MAJOR.MINOR.PATCH.')
    return tuple(map(int, match.groups()))
