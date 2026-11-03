"""Locate the pinned runtime subset included in the classroom archive."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def pinned_sdk_root():
    offline = ROOT / 'offline/snpe226'
    if (offline / 'LICENSE.pdf').is_file():
        return offline
    return ROOT / '.build/sdk-public-2.26/qairt/2.26.0.240828'
