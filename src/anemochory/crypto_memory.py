"""
😐 Anemochory Protocol: Secure Memory Wiping

Best-effort secure memory wiping for cryptographic key material.
Uses ctypes to call platform-native memory zeroing functions.

🌑 Dark Harold's Reminder: Python's garbage collector is NOT your friend
   when it comes to key material. Immutable bytes linger in memory until
   GC decides to collect them, and even then the memory isn't zeroed.
   This module provides tools to fight that — imperfectly.

📺 The History of Memory Wiping:
   OpenSSL uses OPENSSL_cleanse(). libsodium uses sodium_memzero().
   CPython uses... optimism. We bridge that gap with ctypes, knowing
   that the runtime may still betray us with interned references.
"""

from __future__ import annotations

import ctypes
import ctypes.util
import logging
import platform
import sys
from typing import ClassVar


logger = logging.getLogger(__name__)


# ============================================================================
# Platform Detection
# ============================================================================


class _PlatformInfo:
    """Detect available secure memory operations for current platform."""

    _instance: ClassVar[_PlatformInfo | None] = None

    def __init__(self) -> None:
        self.system = platform.system()
        self.has_explicit_bzero = False
        self.has_memset = False
        self.has_securezeromemory = False
        self._libc: ctypes.CDLL | None = None
        self._detect()

    @classmethod
    def get(cls) -> _PlatformInfo:
        """Singleton platform info."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _detect(self) -> None:
        """Detect available memory wiping primitives."""
        try:
            if self.system == "Windows":
                self._detect_windows()
            else:
                self._detect_unix()
        except Exception:
            logger.debug(
                "😐 Failed to detect secure memory primitives. Falling back to Python-level wiping."
            )

    def _detect_unix(self) -> None:
        """Detect Unix memory wiping functions."""
        libc_name = ctypes.util.find_library("c")
        if libc_name is None:
            return

        try:
            self._libc = ctypes.CDLL(libc_name)
        except OSError:
            return

        # Check for explicit_bzero (not optimizable by compiler)
        # Available on Linux (glibc 2.25+), FreeBSD, OpenBSD
        if hasattr(self._libc, "explicit_bzero"):
            self.has_explicit_bzero = True
            logger.debug("🌑 explicit_bzero available — good for key wiping")

        # Fallback: memset (may be optimized away by compiler, but
        # ctypes calls should be safe from dead-store elimination)
        if hasattr(self._libc, "memset"):
            self.has_memset = True

    def _detect_windows(self) -> None:
        """Detect Windows memory wiping functions."""
        try:
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            if hasattr(kernel32, "RtlSecureZeroMemory"):
                self.has_securezeromemory = True
                logger.debug("🌑 RtlSecureZeroMemory available")
            # SecureZeroMemory is a macro that calls RtlSecureZeroMemory
        except (AttributeError, OSError):
            pass

        # Fallback: msvcrt memset
        try:
            msvcrt = ctypes.cdll.msvcrt  # type: ignore[attr-defined]
            if hasattr(msvcrt, "memset"):
                self.has_memset = True
                self._libc = msvcrt
        except (AttributeError, OSError):
            pass


# ============================================================================
# Secure Memory Operations
# ============================================================================


def secure_zero_memory(data: bytearray | memoryview) -> bool:
    """
    Securely zero memory containing sensitive data.

    Uses platform-native functions to avoid dead-store elimination:
    - Linux/BSD: explicit_bzero() (not optimizable)
    - Windows: RtlSecureZeroMemory() (not optimizable)
    - Fallback: ctypes memset (safe from Python-level optimization)
    - Last resort: Python-level byte-by-byte zeroing

    Args:
        data: Mutable buffer to zero (bytearray or memoryview)

    Returns:
        True if platform-native zeroing was used, False for Python fallback

    🌑 This function MUST be called before releasing key material.
    It's not perfect (Python may have copies), but it's the best
    we can do without C extensions.

    😐 bytes objects are immutable and CANNOT be zeroed. Convert to
    bytearray first if you need to wipe key material.
    """
    if not isinstance(data, (bytearray, memoryview)):
        logger.warning(
            "🌑 secure_zero_memory called with %s — cannot zero immutable data",
            type(data).__name__,
        )
        return False

    size = len(data)
    if size == 0:
        return True

    info = _PlatformInfo.get()

    # Get pointer to underlying buffer
    try:
        buf = (ctypes.c_char * size).from_buffer(data)
        ptr = ctypes.cast(buf, ctypes.c_void_p)
    except (TypeError, ValueError):
        # from_buffer failed — fall through to Python fallback
        return _python_zero(data)

    # Strategy 1: explicit_bzero (Linux/BSD — not optimizable)
    if info.has_explicit_bzero and info._libc is not None:
        try:
            info._libc.explicit_bzero(ptr, ctypes.c_size_t(size))
            return True
        except (OSError, ctypes.ArgumentError):
            pass

    # Strategy 2: RtlSecureZeroMemory (Windows — not optimizable)
    if info.has_securezeromemory:
        try:
            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            kernel32.RtlSecureZeroMemory(ptr, ctypes.c_size_t(size))
            return True
        except (AttributeError, OSError, ctypes.ArgumentError):
            pass

    # Strategy 3: ctypes memset (cross-platform — safe from Python optim)
    if info.has_memset and info._libc is not None:
        try:
            info._libc.memset(ptr, 0, ctypes.c_size_t(size))
            return True
        except (OSError, ctypes.ArgumentError):
            pass

    # Strategy 4: Python-level fallback
    return _python_zero(data)


def _python_zero(data: bytearray | memoryview) -> bool:
    """
    Python-level byte-by-byte zeroing.

    🌑 This is the fallback of last resort. It works, but:
    - The Python runtime may have cached copies
    - The GC may not immediately reclaim memory
    - The OS may swap zeroed pages to disk before overwrite

    Still better than nothing. Harold smiles nervously.
    """
    if isinstance(data, memoryview):
        for i in range(len(data)):
            data[i] = 0
    else:
        for i in range(len(data)):
            data[i] = 0
    return False  # Indicates native zeroing wasn't available


def secure_zero_and_del(data: bytearray) -> None:
    """
    Zero a bytearray and attempt to free it immediately.

    Convenience function combining secure_zero_memory + del.

    Args:
        data: Mutable buffer to zero and release

    😐 After this call, `data` should NOT be referenced again.
    Python's GC will eventually collect the object, but we've
    done our best to ensure the memory doesn't contain key material.
    """
    secure_zero_memory(data)
    # Force deletion of the reference
    # (actual memory freeing depends on GC and refcount)
    try:
        data.clear()
    except BufferError:
        # 😐 ctypes from_buffer may hold an export reference
        # The memory is already zeroed, so clear() is nice-to-have
        pass


def key_to_mutable(key: bytes) -> bytearray:
    """
    Convert an immutable key to a mutable bytearray for secure handling.

    Args:
        key: Immutable bytes key material

    Returns:
        Mutable bytearray copy that can be securely zeroed

    🌑 The original bytes object may still exist in memory.
    This is a fundamental Python limitation. We create a mutable
    copy so that at least ONE copy can be reliably wiped.
    """
    return bytearray(key)


def get_memory_security_status() -> dict[str, bool | str]:
    """
    Report on available secure memory capabilities.

    Returns:
        Dictionary describing platform memory security features

    😐 Useful for security audits and debug logging.
    """
    info = _PlatformInfo.get()
    return {
        "platform": info.system,
        "python_version": sys.version,
        "has_explicit_bzero": info.has_explicit_bzero,
        "has_memset": info.has_memset,
        "has_securezeromemory": info.has_securezeromemory,
        "best_method": (
            "explicit_bzero"
            if info.has_explicit_bzero
            else "RtlSecureZeroMemory"
            if info.has_securezeromemory
            else "ctypes_memset"
            if info.has_memset
            else "python_fallback"
        ),
    }
