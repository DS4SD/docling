"""Plugin manager for Docling plugins."""

import re
from typing import List, Dict
from docling.datamodel.document import InputDocument, ConversionResult
from docling.plugins.base import DoclingPlugin
from docling.plugins.models import PluginMetadata

class PluginManager:
    """Manages the registration and execution of Docling plugins."""

    NAME_PATTERN = re.compile(r'^[a-zA-Z][a-zA-Z0-9_-]*$')

    def __init__(self):
        self.preprocessors: List[DoclingPlugin] = []
        self.postprocessors: List[DoclingPlugin] = []
        self._registered_names: Dict[str, DoclingPlugin] = {}

    def _validate_plugin_name(self, name: str) -> None:
        """Validate plugin name format."""
        if not name or name.isspace():
            raise ValueError("Plugin name cannot be empty or whitespace")
        if not self.NAME_PATTERN.match(name):
            raise ValueError(
                "Plugin name must start with a letter and contain only "
                "letters, numbers, underscores, or hyphens"
            )

    def _validate_plugin(self, plugin: DoclingPlugin) -> None:
        """Validate all aspects of a plugin."""
        if not isinstance(plugin, DoclingPlugin):
            raise ValueError(f"Plugin must be an instance of DoclingPlugin, got {type(plugin)}")
        
        self._validate_plugin_name(plugin.name)

        if plugin.name in self._registered_names:
            raise ValueError(f"A plugin with name '{plugin.name}' is already registered")

        if not plugin.metadata:
            raise ValueError(f"Plugin '{plugin.name}' must have metadata")

        # Validate metadata against PluginMetadata model
        try:
            # Convert metadata to dict if it's already a PluginMetadata instance
            metadata_dict = (
                plugin.metadata.model_dump() 
                if isinstance(plugin.metadata, PluginMetadata) 
                else plugin.metadata
            )
            PluginMetadata(**metadata_dict)
        except Exception as e:
            raise ValueError(f"Invalid metadata for plugin '{plugin.name}': {str(e)}")

        # Check if the plugin implements at least one of the processing steps
        if plugin.preprocess.__func__ is DoclingPlugin.preprocess and plugin.postprocess.__func__ is DoclingPlugin.postprocess:
            raise ValueError(
                f"Plugin '{plugin.name}' must implement at least a preprocessing or postprocessing step"
            )

    def register_plugin(self, plugin: DoclingPlugin) -> None:
        """Register a plugin."""
        if plugin is None:
            raise ValueError("Plugin cannot be None")

        self._validate_plugin(plugin)
        self._registered_names[plugin.name] = plugin
        self.preprocessors.append(plugin)
        self.postprocessors.append(plugin)

    def _execute_plugins(self, items: List[DoclingPlugin], data):
        """Execute a sequence of plugins."""
        for plugin in items:
            try:
                data = plugin.preprocess(data) if isinstance(data, InputDocument) else plugin.postprocess(data)
            except Exception as e:
                stage = "preprocessor" if isinstance(data, InputDocument) else "postprocessor"
                raise RuntimeError(f"Error in {stage} {plugin.__class__.__name__}: {str(e)}") from e
        return data

    def execute_preprocessors(self, input_doc: InputDocument) -> InputDocument:
        """Execute all preprocessors."""
        if input_doc is None:
            raise ValueError("Input document cannot be None")
        return self._execute_plugins(self.preprocessors, input_doc)

    def execute_postprocessors(self, result: ConversionResult) -> ConversionResult:
        """Execute all postprocessors."""
        if result is None:
            raise ValueError("Conversion result cannot be None")
        return self._execute_plugins(self.postprocessors, result)
