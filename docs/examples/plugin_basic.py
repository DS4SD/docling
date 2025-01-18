from datetime import datetime
from docling.datamodel.document import InputDocument, ConversionResult
from docling.document_converter import DocumentConverter
from docling.plugins import DoclingPlugin, PluginMetadata

class BasicPlugin(DoclingPlugin):
    """Example plugin that adds metadata and modifies text."""
    
    def __init__(self):
        super().__init__(
            name="BasicPlugin",
            metadata=PluginMetadata(
                version="0.1.0",
                description="A basic plugin that adds processing metadata and modifies text after conversion.",
                author="Ayoub EL BOUCHTILI",
                preprocess={},
                postprocess={}
            )
        )
    
    def preprocess(self, input_doc: InputDocument) -> InputDocument:
        """Add custom metadata during preprocessing."""
        if not hasattr(input_doc, '_plugin_metadata'):
            input_doc._plugin_metadata = {}
        
        self.metadata.preprocess = {
            "timestamp": datetime.now().isoformat()
        }
        return input_doc
    
    def postprocess(self, result: ConversionResult) -> ConversionResult:
        """Add metadata during postprocessing and modify text."""
        
        extra_text = f"[Processed by {self.name}]"
        
        if result.document and result.document.texts:
            # Add a note to the first text item
            first_text = result.document.texts[0]
            first_text.text = f"{extra_text} {first_text.text}"

        # Update postprocessing metadata properly
        self.metadata.postprocess = {
            "appended_text": extra_text,
            "timestamp": datetime.now().isoformat()
        }

        # Append plugin metadata to the result
        if self.name not in result.plugins:
            result.plugins[self.name] = self.metadata.model_dump()
            
        return result

def main():
    # Create plugin instance
    basic_plugin = BasicPlugin()

    # Initialize converter with a plugin
    converter = DocumentConverter(plugins=[basic_plugin])

    # Convert a document
    result = converter.convert("./tests/data/docx/word_sample.docx")
    print(f"Conversion completed with status: {result.status}")
    print(f"Plugins metadata: {result.plugins}")

if __name__ == "__main__":
    main() 