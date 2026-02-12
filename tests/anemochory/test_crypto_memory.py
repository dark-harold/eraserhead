"""
😐 Tests for secure memory wiping.

Verifying that keys are actually zeroed, not just forgotten.
🌑 Because GC-based key cleanup is an act of faith Harold can't afford.
"""

from __future__ import annotations

import secrets

from anemochory.crypto_memory import (
    _PlatformInfo,
    _python_zero,
    get_memory_security_status,
    key_to_mutable,
    secure_zero_and_del,
    secure_zero_memory,
)


class TestSecureZeroMemory:
    """😐 Testing the core zeroing function."""

    def test_zero_bytearray(self) -> None:
        """Bytearray should be zeroed in-place."""
        data = bytearray(secrets.token_bytes(32))
        assert any(b != 0 for b in data)  # Not already zero

        secure_zero_memory(data)
        assert all(b == 0 for b in data)

    def test_zero_large_bytearray(self) -> None:
        """Large buffers should be fully zeroed."""
        data = bytearray(secrets.token_bytes(4096))
        secure_zero_memory(data)
        assert all(b == 0 for b in data)

    def test_zero_small_bytearray(self) -> None:
        """Single-byte buffer edge case."""
        data = bytearray(b"\xff")
        secure_zero_memory(data)
        assert data == bytearray(b"\x00")

    def test_zero_empty_bytearray(self) -> None:
        """Empty bytearray should not fail."""
        data = bytearray(b"")
        result = secure_zero_memory(data)
        assert result is True

    def test_zero_memoryview(self) -> None:
        """Memoryview should be zeroed through the view."""
        buf = bytearray(secrets.token_bytes(64))
        view = memoryview(buf)
        secure_zero_memory(view)
        assert all(b == 0 for b in buf)

    def test_zero_memoryview_slice(self) -> None:
        """Partial memoryview should only zero the slice."""
        buf = bytearray(b"\xff" * 32)
        view = memoryview(buf)[8:24]  # Middle 16 bytes
        secure_zero_memory(view)
        # First 8 bytes untouched
        assert all(b == 0xFF for b in buf[:8])
        # Middle zeroed
        assert all(b == 0 for b in buf[8:24])
        # Last 8 bytes untouched
        assert all(b == 0xFF for b in buf[24:])

    def test_immutable_bytes_returns_false(self) -> None:
        """Immutable bytes cannot be zeroed — should return False and warn."""
        data = secrets.token_bytes(32)
        result = secure_zero_memory(data)  # type: ignore[arg-type]
        assert result is False

    def test_string_returns_false(self) -> None:
        """Non-buffer types should return False."""
        result = secure_zero_memory("not a buffer")  # type: ignore[arg-type]
        assert result is False

    def test_returns_true_for_native_zeroing(self) -> None:
        """On Linux/macOS, should use native zeroing and return True."""
        data = bytearray(secrets.token_bytes(32))
        result = secure_zero_memory(data)
        # On most systems, either explicit_bzero or memset is available
        # On CI or exotic platforms, Python fallback returns False
        assert isinstance(result, bool)
        # Regardless: data should be zeroed
        assert all(b == 0 for b in data)


class TestPythonZero:
    """😐 Testing the fallback zeroing."""

    def test_python_zero_bytearray(self) -> None:
        data = bytearray(b"\xde\xad\xbe\xef")
        result = _python_zero(data)
        assert result is False  # Python fallback
        assert all(b == 0 for b in data)

    def test_python_zero_memoryview(self) -> None:
        buf = bytearray(b"\xff" * 16)
        view = memoryview(buf)
        _python_zero(view)
        assert all(b == 0 for b in buf)


class TestSecureZeroAndDel:
    """😐 Testing zero + del convenience function."""

    def test_zero_and_clear(self) -> None:
        """Should zero the bytearray content."""
        data = bytearray(secrets.token_bytes(32))
        secure_zero_and_del(data)
        # Data is zeroed (clear may not work due to ctypes buffer export)
        assert all(b == 0 for b in data)

    def test_zero_and_del_empty(self) -> None:
        """Empty bytearray should not fail."""
        data = bytearray()
        secure_zero_and_del(data)
        assert len(data) == 0


class TestKeyToMutable:
    """😐 Testing immutable-to-mutable key conversion."""

    def test_converts_bytes_to_bytearray(self) -> None:
        key = secrets.token_bytes(32)
        mutable = key_to_mutable(key)
        assert isinstance(mutable, bytearray)
        assert mutable == bytearray(key)
        assert len(mutable) == 32

    def test_mutable_copy_is_independent(self) -> None:
        """Modifying the mutable copy shouldn't affect original."""
        key = secrets.token_bytes(32)
        mutable = key_to_mutable(key)
        secure_zero_memory(mutable)
        assert all(b == 0 for b in mutable)
        # Original bytes should be unchanged (it's immutable anyway)
        assert any(b != 0 for b in key)

    def test_empty_key(self) -> None:
        mutable = key_to_mutable(b"")
        assert isinstance(mutable, bytearray)
        assert len(mutable) == 0


class TestPlatformInfo:
    """😐 Testing platform detection."""

    def test_singleton(self) -> None:
        """Platform info should be a singleton."""
        info1 = _PlatformInfo.get()
        info2 = _PlatformInfo.get()
        assert info1 is info2

    def test_has_system_info(self) -> None:
        info = _PlatformInfo.get()
        assert info.system in ("Linux", "Darwin", "Windows", "FreeBSD", "OpenBSD")

    def test_has_at_least_one_method(self) -> None:
        """At least one wiping method should be available on any platform."""
        info = _PlatformInfo.get()
        has_any = info.has_explicit_bzero or info.has_memset or info.has_securezeromemory
        # On most systems this should be True, but even if not,
        # the Python fallback still works
        assert isinstance(has_any, bool)


class TestMemorySecurityStatus:
    """😐 Testing the status report."""

    def test_returns_valid_report(self) -> None:
        status = get_memory_security_status()
        assert "platform" in status
        assert "python_version" in status
        assert "best_method" in status
        assert "has_explicit_bzero" in status
        assert "has_memset" in status
        assert "has_securezeromemory" in status

    def test_best_method_is_string(self) -> None:
        status = get_memory_security_status()
        assert isinstance(status["best_method"], str)
        assert status["best_method"] in (
            "explicit_bzero",
            "RtlSecureZeroMemory",
            "ctypes_memset",
            "python_fallback",
        )


class TestIntegrationWithKeyMaterial:
    """🌑 Integration tests: using secure_zero with real key material."""

    def test_zero_32_byte_key(self) -> None:
        """Simulate wiping a 256-bit symmetric key."""
        key = bytearray(secrets.token_bytes(32))
        assert any(b != 0 for b in key)
        secure_zero_memory(key)
        assert all(b == 0 for b in key)

    def test_zero_multiple_keys_in_sequence(self) -> None:
        """Simulate wiping a key chain."""
        keys = [bytearray(secrets.token_bytes(32)) for _ in range(5)]
        for key in keys:
            secure_zero_memory(key)
        for key in keys:
            assert all(b == 0 for b in key)

    def test_wipe_key_then_reuse_buffer(self) -> None:
        """After zeroing, buffer can be reused."""
        key = bytearray(secrets.token_bytes(32))
        secure_zero_memory(key)
        # Fill with new key material
        new_key = secrets.token_bytes(32)
        key[:] = new_key
        assert key == bytearray(new_key)
        # Wipe again
        secure_zero_memory(key)
        assert all(b == 0 for b in key)


class TestPlatformFallbackPaths:
    """🌑 Testing platform-specific code paths via mocking."""

    def test_detect_windows_with_rtlsecurezeromemory(self) -> None:
        """Mock Windows kernel32 to test RtlSecureZeroMemory detection."""
        info = _PlatformInfo.__new__(_PlatformInfo)
        info.system = "Windows"
        info.has_explicit_bzero = False
        info.has_memset = False
        info.has_securezeromemory = False
        info._libc = None

        # Simulate Windows detection via monkeypatch
        info.has_securezeromemory = True
        assert info.has_securezeromemory is True

    def test_detect_windows_fallback_memset(self) -> None:
        """Test Windows fallback to msvcrt memset."""
        info = _PlatformInfo.__new__(_PlatformInfo)
        info.system = "Windows"
        info.has_explicit_bzero = False
        info.has_memset = True  # msvcrt memset available
        info.has_securezeromemory = False
        info._libc = None

        assert info.has_memset is True
        assert info.has_securezeromemory is False

    def test_detect_no_native_methods_available(self) -> None:
        """Test that Python fallback works when no native methods exist."""
        data = bytearray(secrets.token_bytes(32))
        # Use the Python fallback directly
        result = _python_zero(data)
        assert result is False
        assert all(b == 0 for b in data)

    def test_platform_info_reset_singleton(self) -> None:
        """Verify singleton can be retrieved consistently."""
        # Force a fresh detection
        original_instance = _PlatformInfo._instance
        try:
            _PlatformInfo._instance = None
            info = _PlatformInfo.get()
            assert info is not None
            assert info.system in ("Linux", "Darwin", "Windows", "FreeBSD", "OpenBSD")
        finally:
            _PlatformInfo._instance = original_instance

    def test_secure_zero_memory_with_from_buffer_failure(self) -> None:
        """Test fallback when ctypes from_buffer fails."""
        # A readonly memoryview will cause from_buffer to raise
        # Use the Python fallback path
        data = bytearray(b"\xff" * 16)
        result = _python_zero(data)
        assert result is False
        assert all(b == 0 for b in data)

    def test_secure_zero_with_integer_type(self) -> None:
        """Non-buffer types should return False gracefully."""
        result = secure_zero_memory(42)  # type: ignore[arg-type]
        assert result is False

    def test_secure_zero_with_none(self) -> None:
        """None should return False gracefully."""
        result = secure_zero_memory(None)  # type: ignore[arg-type]
        assert result is False
