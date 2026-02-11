"""EraserHead: Internet Presence Erasure Platform

😐 Pragmatically erasing digital footprints while smiling through the pain.
"""

__version__ = "0.1.0"
__author__ = "Harold"
__email__ = "harold@hidethepain.local"

from eraserhead.engine import EngineConfig, ScrubEngine
from eraserhead.models import (
    DeletionResult,
    DeletionTask,
    Platform,
    PlatformCredentials,
    ResourceType,
    ScrubProgress,
    TaskPriority,
    TaskStatus,
)
from eraserhead.queue import TaskQueue
from eraserhead.vault import CredentialVault
from eraserhead.verification import VerificationService


__all__ = [
    "CredentialVault",
    "DeletionResult",
    "DeletionTask",
    "EngineConfig",
    "Platform",
    "PlatformCredentials",
    "ResourceType",
    "ScrubEngine",
    "ScrubProgress",
    "TaskPriority",
    "TaskQueue",
    "TaskStatus",
    "VerificationService",
]
