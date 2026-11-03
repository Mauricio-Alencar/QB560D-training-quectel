"""Provisioning API backed by shared host transport code."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'host'))
from provision_session import Session, RuntimeAdapter, select_device
