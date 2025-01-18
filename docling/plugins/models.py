"""Data models for  DoclingPlugin."""

from typing import Dict, Any
from pydantic import BaseModel, Field

class PluginMetadata(BaseModel):
    """Model for plugin metadata validation.
    
    Attributes:
        version: The plugin version following semantic versioning
        description: A brief description of the plugin's functionality
        author: The plugin author's name
        preprocess: Metadata for preprocessing step
        postprocess: Metadata for postprocessing step
    """
    version: str = Field(
        default="",
        pattern=r"^\d+\.\d+\.\d+$",
        description="Plugin version (semantic versioning)"
    )
    description: str = Field(
        default="",
        description="Brief description of the plugin"
    )
    author: str = Field(
        default="",
        description="Plugin author's name"
    )
    preprocess: Dict[str, Any] = Field(
        default_factory=dict,
        description="Preprocessing related metadata"
    )
    postprocess: Dict[str, Any] = Field(
        default_factory=dict,
        description="Postprocessing related metadata"
    ) 