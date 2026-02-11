"""
😐 Pytest Configuration for EraserHead

Shared fixtures, configuration, and test utilities.

🌑 Dark Harold's Testing Standards:
    - >80% code coverage (enforced)
    - Property-based testing for crypto (Hypothesis)
    - Timing analysis for constant-time operations
    - Fuzzing for packet parsing
    - Security reviews before release
"""

import pytest


# 😐 harold-tester: Fixtures will be added as needed
# Week 4: Crypto fixtures (keys, engines, test vectors)
# Week 5: Network fixtures (mock nodes, packet builders)
# Week 6: Integration fixtures (multi-hop simulations)


@pytest.fixture
def sample_key():
    """Generate a 32-byte test key.

    😐 For testing only. Production keys use ChaCha20Engine.generate_key()
    """
    return b"\x00" * 32  # Simple test key (zeros for deterministic tests)


@pytest.fixture
def sample_master_key():
    """Master key for multi-layer encryption tests."""
    return b"\x01" * 32


# 😐 Pytest CLI options
def pytest_addoption(parser):
    """Add custom CLI options.

    Usage:
        pytest --slow  # Run slow tests (timing analysis, fuzzing)
    """
    parser.addoption(
        "--slow",
        action="store_true",
        default=False,
        help="Run slow tests (timing analysis, fuzzing)",
    )


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow (timing, fuzzing)")
    config.addinivalue_line("markers", "crypto: cryptography tests")
    config.addinivalue_line("markers", "network: network-related tests")
    config.addinivalue_line("markers", "integration: integration tests")


def pytest_collection_modifyitems(config, items):
    """Skip slow tests unless --slow flag provided."""
    if config.getoption("--slow"):
        return  # Run all tests

    skip_slow = pytest.mark.skip(reason="need --slow option to run")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


# 🌑 Dark Harold's test execution notes:
# - Run tests frequently: pytest
# - Run with coverage: pytest --cov=src --cov-report=html
# - Run only crypto tests: pytest -m crypto
# - Run integration tests: pytest -m integration
# - Run slow tests: pytest --slow
# - Run in parallel: pytest -n auto
