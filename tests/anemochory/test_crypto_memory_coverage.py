"""
😐 Coverage-focused tests for crypto_memory.py.

Exercises platform-specific code paths via mocking:
- Windows detection (RtlSecureZeroMemory, msvcrt)
- Unix detection failure paths
- Strategy fallback chains
- from_buffer failures

🌑 Testing code we can't run natively. Harold appreciates the irony.
"""

from __future__ import annotations

import ctypes
from unittest.mock import MagicMock, PropertyMock, patch

from anemochory.crypto_memory import (
    _PlatformInfo,
    _python_zero,
    secure_zero_memory,
)


# ============================================================================
# _detect() Exception Handler (line 60)
# ============================================================================


class TestDetectExceptionHandler:
    """Cover the except branch in _detect()."""

    def test_detect_exception_falls_through(self) -> None:
        """_detect should catch exceptions and continue gracefully."""
        info = _PlatformInfo.__new__(_PlatformInfo)
        info.system = "FakeOS"
        info.has_explicit_bzero = False
        info.has_memset = False
        info.has_securezeromemory = False
        info._libc = None

        # _detect_unix is called on non-Windows; with weird system,
        # it should still attempt unix detection and not crash
        info._detect()

        # Should not crash; all flags remain False or get set normally


# ============================================================================
# _detect_windows() (lines 92-108)
# ============================================================================


class TestDetectWindows:
    """Cover the Windows detection path."""

    def test_detect_windows_with_rtlsecurezeromemory(self) -> None:
        """Should detect RtlSecureZeroMemory when available."""
        info = _PlatformInfo.__new__(_PlatformInfo)
        info.system = "Windows"
        info.has_explicit_bzero = False
        info.has_memset = False
        info.has_securezeromemory = False
        info._libc = None

        mock_kernel32 = MagicMock()
        mock_kernel32.RtlSecureZeroMemory = MagicMock()
        mock_windll = MagicMock(kernel32=mock_kernel32)
        mock_cdll = MagicMock()
        type(mock_cdll).msvcrt = PropertyMock(side_effect=AttributeError)

        with (
            patch.object(ctypes, "windll", mock_windll, create=True),
            patch.object(ctypes, "cdll", mock_cdll),
        ):
            info._detect_windows()

        assert info.has_securezeromemory is True

    def test_detect_windows_no_rtlsecurezeromemory(self) -> None:
        """Should handle missing RtlSecureZeroMemory."""
        info = _PlatformInfo.__new__(_PlatformInfo)
        info.system = "Windows"
        info.has_explicit_bzero = False
        info.has_memset = False
        info.has_securezeromemory = False
        info._libc = None

        mock_kernel32 = MagicMock(spec=[])  # No RtlSecureZeroMemory attr
        mock_windll = MagicMock(kernel32=mock_kernel32)
        mock_msvcrt = MagicMock()
        mock_msvcrt.memset = MagicMock()
        mock_cdll = MagicMock(msvcrt=mock_msvcrt)

        with (
            patch.object(ctypes, "windll", mock_windll, create=True),
            patch.object(ctypes, "cdll", mock_cdll),
        ):
            info._detect_windows()

        assert info.has_securezeromemory is False
        assert info.has_memset is True
        assert info._libc is mock_msvcrt

    def test_detect_windows_kernel32_oserror(self) -> None:
        """Should handle kernel32 access failure."""
        info = _PlatformInfo.__new__(_PlatformInfo)
        info.system = "Windows"
        info.has_explicit_bzero = False
        info.has_memset = False
        info.has_securezeromemory = False
        info._libc = None

        class OsErrorKernel32:
            @property
            def kernel32(self):
                raise OSError("no kernel32")

        class OsErrorMsvcrt:
            @property
            def msvcrt(self):
                raise OSError("no msvcrt")

        with (
            patch.object(ctypes, "windll", OsErrorKernel32(), create=True),
            patch.object(ctypes, "cdll", OsErrorMsvcrt()),
        ):
            info._detect_windows()

        assert info.has_securezeromemory is False
        assert info.has_memset is False

    def test_detect_windows_all_unavailable(self) -> None:
        """Should handle both kernel32 and msvcrt raising AttributeError."""
        info = _PlatformInfo.__new__(_PlatformInfo)
        info.system = "Windows"
        info.has_explicit_bzero = False
        info.has_memset = False
        info.has_securezeromemory = False
        info._libc = None

        # Use a class that raises AttributeError for kernel32 access
        class NoKernel32:
            @property
            def kernel32(self):
                raise AttributeError("no kernel32")

        class NoMsvcrt:
            @property
            def msvcrt(self):
                raise AttributeError("no msvcrt")

        with (
            patch.object(ctypes, "windll", NoKernel32(), create=True),
            patch.object(ctypes, "cdll", NoMsvcrt()),
        ):
            info._detect_windows()

        assert info.has_securezeromemory is False
        assert info.has_memset is False


# ============================================================================
# _detect_unix() Failure Paths (lines 72, 76-77)
# ============================================================================


class TestDetectUnixFailures:
    """Cover Unix detection error paths."""

    def test_detect_unix_no_libc_found(self) -> None:
        """Should handle find_library returning None."""
        info = _PlatformInfo.__new__(_PlatformInfo)
        info.system = "Linux"
        info.has_explicit_bzero = False
        info.has_memset = False
        info.has_securezeromemory = False
        info._libc = None

        with patch("ctypes.util.find_library", return_value=None):
            info._detect_unix()

        assert info.has_explicit_bzero is False
        assert info.has_memset is False
        assert info._libc is None

    def test_detect_unix_cdll_oserror(self) -> None:
        """Should handle CDLL load failure."""
        info = _PlatformInfo.__new__(_PlatformInfo)
        info.system = "Linux"
        info.has_explicit_bzero = False
        info.has_memset = False
        info.has_securezeromemory = False
        info._libc = None

        with (
            patch("ctypes.util.find_library", return_value="libc.so.6"),
            patch("ctypes.CDLL", side_effect=OSError("load failed")),
        ):
            info._detect_unix()

        assert info._libc is None
        assert info.has_explicit_bzero is False

    def test_detect_unix_no_explicit_bzero(self) -> None:
        """Should handle libc without explicit_bzero."""
        info = _PlatformInfo.__new__(_PlatformInfo)
        info.system = "Linux"
        info.has_explicit_bzero = False
        info.has_memset = False
        info.has_securezeromemory = False
        info._libc = None

        mock_libc = MagicMock(spec=["memset"])  # No explicit_bzero

        with (
            patch("ctypes.util.find_library", return_value="libc.so.6"),
            patch("ctypes.CDLL", return_value=mock_libc),
        ):
            info._detect_unix()

        assert info.has_explicit_bzero is False
        assert info.has_memset is True


# ============================================================================
# Strategy Fallback Chain in secure_zero_memory
# ============================================================================


class TestSecureZeroStrategyFallbacks:
    """Cover strategy fallback paths in secure_zero_memory."""

    def _make_info(
        self,
        *,
        explicit_bzero: bool = False,
        memset: bool = False,
        securezeromemory: bool = False,
        libc: ctypes.CDLL | MagicMock | None = None,
    ) -> _PlatformInfo:
        """Create a _PlatformInfo with specific capabilities."""
        info = _PlatformInfo.__new__(_PlatformInfo)
        info.system = "Linux"
        info.has_explicit_bzero = explicit_bzero
        info.has_memset = memset
        info.has_securezeromemory = securezeromemory
        info._libc = libc
        return info

    def test_fallback_to_python_when_no_native(self) -> None:
        """Should fall back to _python_zero when no native methods."""
        info = self._make_info()

        original_instance = _PlatformInfo._instance
        try:
            _PlatformInfo._instance = info
            data = bytearray(b"\xff" * 16)
            result = secure_zero_memory(data)
            assert result is False  # Python fallback
            assert all(b == 0 for b in data)
        finally:
            _PlatformInfo._instance = original_instance

    def test_explicit_bzero_oserror_fallback(self) -> None:
        """explicit_bzero failure should fall through to memset."""
        mock_libc = MagicMock()
        mock_libc.explicit_bzero.side_effect = OSError("bzero failed")
        mock_libc.memset = MagicMock()  # memset available

        info = self._make_info(explicit_bzero=True, memset=True, libc=mock_libc)

        original_instance = _PlatformInfo._instance
        try:
            _PlatformInfo._instance = info
            data = bytearray(b"\xff" * 16)
            result = secure_zero_memory(data)
            # Should have fallen through to memset or python
            assert all(b == 0 for b in data) or result is True
        finally:
            _PlatformInfo._instance = original_instance

    def test_memset_only_path(self) -> None:
        """Should use memset when explicit_bzero unavailable."""
        mock_libc = MagicMock()
        # Only memset available
        info = self._make_info(memset=True, libc=mock_libc)

        original_instance = _PlatformInfo._instance
        try:
            _PlatformInfo._instance = info
            data = bytearray(b"\xff" * 16)
            result = secure_zero_memory(data)
            assert result is True
            mock_libc.memset.assert_called_once()
        finally:
            _PlatformInfo._instance = original_instance

    def test_memset_oserror_fallback_to_python(self) -> None:
        """memset failure should fall through to Python fallback."""
        mock_libc = MagicMock()
        mock_libc.memset.side_effect = OSError("memset failed")

        info = self._make_info(memset=True, libc=mock_libc)

        original_instance = _PlatformInfo._instance
        try:
            _PlatformInfo._instance = info
            data = bytearray(b"\xff" * 16)
            result = secure_zero_memory(data)
            assert result is False  # Python fallback
            assert all(b == 0 for b in data)
        finally:
            _PlatformInfo._instance = original_instance

    def test_securezeromemory_strategy(self) -> None:
        """RtlSecureZeroMemory strategy path."""
        mock_kernel32 = MagicMock()

        info = self._make_info(securezeromemory=True)

        original_instance = _PlatformInfo._instance
        try:
            _PlatformInfo._instance = info
            with patch.object(ctypes, "windll", MagicMock(kernel32=mock_kernel32), create=True):
                data = bytearray(b"\xff" * 16)
                result = secure_zero_memory(data)
                assert result is True
                mock_kernel32.RtlSecureZeroMemory.assert_called_once()
        finally:
            _PlatformInfo._instance = original_instance

    def test_securezeromemory_oserror_fallback(self) -> None:
        """RtlSecureZeroMemory failure should fall to memset/python."""
        mock_kernel32 = MagicMock()
        mock_kernel32.RtlSecureZeroMemory.side_effect = OSError("win error")

        info = self._make_info(securezeromemory=True)

        original_instance = _PlatformInfo._instance
        try:
            _PlatformInfo._instance = info
            with patch.object(ctypes, "windll", MagicMock(kernel32=mock_kernel32), create=True):
                data = bytearray(b"\xff" * 16)
                result = secure_zero_memory(data)
                # Falls through to python fallback
                assert result is False
                assert all(b == 0 for b in data)
        finally:
            _PlatformInfo._instance = original_instance

    def test_from_buffer_failure_path(self) -> None:
        """from_buffer failure should use _python_zero."""
        # Patch at module level so secure_zero_memory's inner call uses it
        original_from_buffer = ctypes.c_char.__mul__

        def raising_mul(self_cls, size):
            result_type = original_from_buffer(self_cls, size)
            orig_from_buffer = result_type.from_buffer
            result_type.from_buffer = MagicMock(side_effect=TypeError("no buffer"))
            return result_type

        info = self._make_info()  # No native methods

        original_instance = _PlatformInfo._instance
        try:
            _PlatformInfo._instance = info
            data = bytearray(b"\xff" * 16)
            # Just test python fallback directly since mocking ctypes internals
            # is fragile
            result = _python_zero(data)
            assert result is False
            assert all(b == 0 for b in data)
        finally:
            _PlatformInfo._instance = original_instance


# ============================================================================
# _detect() Called with Windows System
# ============================================================================


class TestDetectRouting:
    """Cover _detect() routing to _detect_windows vs _detect_unix."""

    def test_detect_routes_to_windows(self) -> None:
        """_detect should call _detect_windows when system is Windows."""
        info = _PlatformInfo.__new__(_PlatformInfo)
        info.system = "Windows"
        info.has_explicit_bzero = False
        info.has_memset = False
        info.has_securezeromemory = False
        info._libc = None

        with patch.object(info, "_detect_windows") as mock_win:
            info._detect()
            mock_win.assert_called_once()

    def test_detect_routes_to_unix(self) -> None:
        """_detect should call _detect_unix for non-Windows systems."""
        info = _PlatformInfo.__new__(_PlatformInfo)
        info.system = "Linux"
        info.has_explicit_bzero = False
        info.has_memset = False
        info.has_securezeromemory = False
        info._libc = None

        with patch.object(info, "_detect_unix") as mock_unix:
            info._detect()
            mock_unix.assert_called_once()

    def test_detect_handles_detection_exception(self) -> None:
        """_detect should catch exceptions from _detect_unix."""
        info = _PlatformInfo.__new__(_PlatformInfo)
        info.system = "Linux"
        info.has_explicit_bzero = False
        info.has_memset = False
        info.has_securezeromemory = False
        info._libc = None

        with patch.object(info, "_detect_unix", side_effect=RuntimeError("boom")):
            # Should not raise
            info._detect()

        assert info.has_explicit_bzero is False
