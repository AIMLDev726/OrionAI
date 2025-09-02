"""
Test configuration and fixtures for OrionAI tests.
"""

import os
import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def mock_api_key():
    """Provide a mock API key for testing."""
    return "test-api-key-12345"


@pytest.fixture
def mock_google_provider():
    """Mock Google provider for testing."""
    with patch('orionai.python.aipython.GoogleProvider') as mock:
        mock_instance = Mock()
        mock_instance.generate.return_value = "Mock response"
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_openai_provider():
    """Mock OpenAI provider for testing."""
    with patch('orionai.python.aipython.OpenAIProvider') as mock:
        mock_instance = Mock()
        mock_instance.generate.return_value = "Mock response"
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace directory."""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir()
    return str(workspace)


@pytest.fixture
def sample_data():
    """Provide sample data for testing."""
    return {
        "numbers": [1, 2, 3, 4, 5],
        "strings": ["hello", "world", "test"],
        "mixed": {"key1": "value1", "key2": 42}
    }


# Test configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
