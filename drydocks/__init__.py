"""
DryDocks: An LLM API test suite for OpenAI-compatible endpoints.
"""

__version__ = "0.1.0"
__author__ = "DryDocks Contributors"

from .config import ConfigManager
from .api import LLMClient
from .runner import TestRunner

__all__ = ["ConfigManager", "LLMClient", "TestRunner", "__version__"]
