"""Processors package initialization."""
from .snapshot_manager import SnapshotManager
from .change_detector import ChangeDetector

__all__ = ['SnapshotManager', 'ChangeDetector']