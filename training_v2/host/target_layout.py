"""Shared target locations for the persistent classroom preparation."""
from pathlib import PurePosixPath

DEFAULT_REMOTE = '/opt/qb560d-training-payload'


def validate_remote(value):
    allowed = (DEFAULT_REMOTE, '/tmp/qb560d-training')
    if value not in allowed or '..' in PurePosixPath(value).parts:
        raise ValueError('--remote must be /opt/qb560d-training-payload or /tmp/qb560d-training')
    return value
