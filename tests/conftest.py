# Epic Games Claimer - Pytest Configuration
"""
Pytest fixtures and configuration for the test suite.
"""

import sys
from pathlib import Path

import pytest


# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Path to test artifacts
ARTIFACTS_DIR = Path(__file__).parent / "artifacts"


@pytest.fixture
def artifacts_dir() -> Path:
    """Return the path to test artifacts directory."""
    return ARTIFACTS_DIR


@pytest.fixture
def sample_html(artifacts_dir: Path) -> str:
    """Load sample HTML dump for testing."""
    html_file = artifacts_dir / "test_html_dump.html"
    if html_file.exists():
        return html_file.read_text(encoding="utf-8")
    return ""


@pytest.fixture
def page_content_sample(artifacts_dir: Path) -> str:
    """Load page content sample for testing."""
    sample_file = artifacts_dir / "page_content_sample.html"
    if sample_file.exists():
        return sample_file.read_text(encoding="utf-8")
    return ""
