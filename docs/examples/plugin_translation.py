from typing import Optional
from datetime import datetime

from docling.datamodel.document import InputDocument, ConversionResult
from docling.plugins import DoclingPlugin, PluginMetadata
from docling_core.types.doc import TextItem, TableItem

class TranslationPlugin(DoclingPlugin):
    """Plugin that translates document text to a target language."""
    
    def __init__(self, target_lang: str, source_lang: Optional[str] = None):
        """Initialize the translation plugin.
        
        Args:
            target_lang: Target language code (e.g. 'fr' for French)
            source_lang: Optional source language code. If not provided,
                        will be auto-detected during translation
        """
        super().__init__(
            name="TranslationPlugin",
            metadata=PluginMetadata(
                version="0.1.0",
                description=f"Translates document text to {target_lang}",
                author="Ayoub EL BOUCHTILI",
                preprocess={},
                postprocess={}
            )
        )
        self.target_lang = target_lang
        self.source_lang = source_lang
        
    def translate_text(self, text: str) -> tuple[str, str]:
        """Translate text to target language.
        
        Args:
            text: Text to translate
            
        Returns:
            Tuple of (translated_text, detected_source_lang)
        """
        # IMPLEMENT YOUR TRANSLATION LOGIC HERE
        # FOR EXAMPLE USING GOOGLE TRANSLATE:

        # from googletrans import Translator
        # translator = Translator()
        # if self.source_lang:
        #     result = translator.translate(text, src=self.source_lang, dest=self.target_lang)
        # else:
        #     result = translator.translate(text, dest=self.target_lang)
        # return result.text, result.src

        # END OF PLACEHOLDER IMPLEMENTATION
        return text, self.source_lang or "en"
    
    def postprocess(self, result: ConversionResult) -> ConversionResult:
        """Translate document text after conversion."""
        
        if result.document and result.document.texts:
            detected_langs = set()
            
            # Translate all text items
            for element in result.document.iterate_items():
                if isinstance(element[0], TextItem):
                    # Translate
                    translated, detected = self.translate_text(element[0].text)
                    element[0].text = translated
                    detected_langs.add(detected)
                    
                elif isinstance(element[0], TableItem):
                    # Handle table cells
                    for cell in element[0].data.table_cells:
                        translated, detected = self.translate_text(cell.text)
                        cell.text = translated
                        detected_langs.add(detected)

        # Add translation metadata
        self.metadata.postprocess = {
            "target_language": self.target_lang,
            "source_languages": list(detected_langs),
            "timestamp": datetime.now().isoformat()
        }
        
        # Add plugin metadata to result
        if self.name not in result.plugins:
            result.plugins[self.name] = self.metadata.model_dump()
            
        return result

def main():
    # Example usage
    from docling.document_converter import DocumentConverter
    
    # Create plugin instance
    translation_plugin = TranslationPlugin(target_lang="fr")
    
    # Initialize converter with plugin
    converter = DocumentConverter(plugins=[translation_plugin])
    
    # Convert a document
    result = converter.convert("./tests/data/docx/word_sample.docx")
    print(f"Conversion completed with status: {result.status}")
    print(f"Plugin metadata: {result.plugins}")

if __name__ == "__main__":
    main()
