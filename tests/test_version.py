"""Tests for the package __version__ export."""
import re

import async_patcher


def test_version_attribute_exists():
    assert hasattr(async_patcher, "__version__")


def test_version_is_a_string():
    assert isinstance(async_patcher.__version__, str)


def test_version_is_non_empty():
    assert async_patcher.__version__ != ""


def test_version_matches_pep_440_or_dev_pattern():
    """Accept anything that looks like a version (PEP 440 or '0.1.0'-style)."""
    assert re.match(r"^\d+\.\d+\.\d+", async_patcher.__version__)
