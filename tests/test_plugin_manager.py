import pytest
from docling.plugins.manager import PluginManager
from docling.plugins.base import DoclingPlugin
from docling.plugins.models import PluginMetadata
from docling.datamodel.document import InputDocument, ConversionResult
from docling.datamodel.base_models import InputFormat
from docling.backend.docling_parse_backend import DoclingParseDocumentBackend

class BasicTestPlugin(DoclingPlugin):
    def __init__(self, name="TestPlugin"):
        super().__init__(
            name=name,
            metadata=PluginMetadata(
                version="0.1.0",
                description="Test plugin",
                author="Test Author"
            )
        )
    
    def preprocess(self, input_doc: InputDocument) -> InputDocument:
        return input_doc

class PreprocessOnlyPlugin(DoclingPlugin):
    def __init__(self):
        super().__init__(
            name="PreprocessPlugin",
            metadata=PluginMetadata(
                version="0.1.0",
                description="Preprocess only plugin",
                author="Test Author"
            )
        )
    
    def preprocess(self, input_doc: InputDocument) -> InputDocument:
        input_doc._test_flag = True
        return input_doc

class PostprocessOnlyPlugin(DoclingPlugin):
    def __init__(self):
        super().__init__(
            name="PostprocessPlugin",
            metadata=PluginMetadata(
                version="0.1.0",
                description="Postprocess only plugin",
                author="Test Author"
            )
        )
    
    def postprocess(self, result: ConversionResult) -> ConversionResult:
        result._test_flag = True
        return result

class ErrorPlugin(DoclingPlugin):
    def __init__(self):
        super().__init__(
            name="ErrorPlugin",
            metadata=PluginMetadata(
                version="0.1.0",
                description="Error plugin",
                author="Test Author"
            )
        )
    
    def preprocess(self, input_doc: InputDocument) -> InputDocument:
        raise ValueError("Test error")

@pytest.fixture
def plugin_manager():
    return PluginManager()

@pytest.fixture
def input_document():
    return InputDocument(
        path_or_stream="test.pdf",
        format=InputFormat.PDF,
        backend=DoclingParseDocumentBackend
    )

@pytest.fixture
def conversion_result(input_document):
    return ConversionResult(input=input_document)

def test_plugin_name_validation(plugin_manager):
    # Test empty name
    with pytest.raises(ValueError, match="Plugin name cannot be empty or whitespace"):
        plugin_manager._validate_plugin_name("")
    
    # Test whitespace name
    with pytest.raises(ValueError, match="Plugin name cannot be empty or whitespace"):
        plugin_manager._validate_plugin_name("   ")
    
    # Test invalid characters
    with pytest.raises(ValueError, match="Plugin name must start with a letter"):
        plugin_manager._validate_plugin_name("123plugin")
    
    # Test valid names
    plugin_manager._validate_plugin_name("validPlugin123")
    plugin_manager._validate_plugin_name("valid_plugin")
    plugin_manager._validate_plugin_name("valid-plugin")

def test_plugin_validation(plugin_manager):
    # Test None plugin
    with pytest.raises(ValueError, match="Plugin cannot be None"):
        plugin_manager.register_plugin(None)
    
    # Test invalid plugin type
    with pytest.raises(ValueError, match="Plugin must be an instance of DoclingPlugin"):
        plugin_manager.register_plugin("not a plugin")
    
    # Test duplicate plugin name
    plugin = BasicTestPlugin()
    plugin_manager.register_plugin(plugin)
    with pytest.raises(ValueError, match="already registered"):
        plugin_manager.register_plugin(BasicTestPlugin())
    
    # Test invalid metadata
    invalid_plugin = BasicTestPlugin(name="InvalidMetadataPlugin")
    invalid_plugin.metadata.version = "invalid"  # Invalid semver
    with pytest.raises(ValueError, match="Invalid metadata"):
        plugin_manager.register_plugin(invalid_plugin)

def test_preprocess_execution(plugin_manager, input_document):
    plugin = PreprocessOnlyPlugin()
    plugin_manager.register_plugin(plugin)
    
    processed_doc = plugin_manager.execute_preprocessors(input_document)
    
    assert hasattr(processed_doc, '_test_flag')
    assert processed_doc._test_flag is True

def test_postprocess_execution(plugin_manager, conversion_result):
    plugin = PostprocessOnlyPlugin()
    plugin_manager.register_plugin(plugin)
    
    processed_result = plugin_manager.execute_postprocessors(conversion_result)
    
    assert hasattr(processed_result, '_test_flag')
    assert processed_result._test_flag is True

def test_plugin_execution_error_handling(plugin_manager, input_document):
    plugin = ErrorPlugin()
    plugin_manager.register_plugin(plugin)
    
    with pytest.raises(RuntimeError, match="Error in preprocessor ErrorPlugin"):
        plugin_manager.execute_preprocessors(input_document)

def test_none_input_validation(plugin_manager):
    with pytest.raises(ValueError, match="Input document cannot be None"):
        plugin_manager.execute_preprocessors(None)
    
    with pytest.raises(ValueError, match="Conversion result cannot be None"):
        plugin_manager.execute_postprocessors(None)

def test_multiple_plugins_execution_order(plugin_manager, input_document):
    class OrderTestPlugin(DoclingPlugin):
        def __init__(self, name, order_list):
            super().__init__(
                name=name,
                metadata=PluginMetadata(
                    version="0.1.0",
                    description="Order test plugin",
                    author="Test Author"
                )
            )
            self.order_list = order_list
        
        def preprocess(self, input_doc: InputDocument) -> InputDocument:
            self.order_list.append(self.name)
            return input_doc
    
    execution_order = []
    plugin1 = OrderTestPlugin("Plugin1", execution_order)
    plugin2 = OrderTestPlugin("Plugin2", execution_order)
    
    plugin_manager.register_plugin(plugin1)
    plugin_manager.register_plugin(plugin2)
    
    plugin_manager.execute_preprocessors(input_document)
    
    assert execution_order == ["Plugin1", "Plugin2"]
