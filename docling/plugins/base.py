"""Base plugin class for Docling plugins."""

from docling.datamodel.document import InputDocument, ConversionResult
from docling.plugins.models import PluginMetadata

class DoclingPlugin:
    """Base class for Docling plugins."""

    def __init__(self, name: str, metadata: PluginMetadata):
        """Initialize the plugin."""
        self.name = name
        self.metadata = metadata

    def preprocess(self, input_doc: InputDocument) -> InputDocument:
        """Preprocess the input document. Default implementation returns the input unmodified."""
        return input_doc

    def postprocess(self, result: ConversionResult) -> ConversionResult:
        """Postprocess the conversion result. Default implementation returns the result unmodified."""
        return result
