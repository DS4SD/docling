"""Docling plugin system for extending document processing capabilities."""

from .base import DoclingPlugin
from .manager import PluginManager
from .models import PluginMetadata

__all__ = ["DoclingPlugin", "PluginManager", "PluginMetadata"] 