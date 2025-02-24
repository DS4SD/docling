import re
from pathlib import Path
from typing import Iterable, List, Literal, Optional, Tuple, Union

import numpy as np
from docling_core.types.doc import (
    CodeItem,
    DocItemLabel,
    DoclingDocument,
    NodeItem,
    TextItem,
)
from docling_core.types.doc.labels import CodeLanguageLabel
from PIL import Image
from pydantic import BaseModel

from docling.datamodel.base_models import ItemAndImageEnrichmentElement
from docling.datamodel.pipeline_options import AcceleratorOptions
from docling.models.base_model import BaseItemAndImageEnrichmentModel
from docling.utils.accelerator_utils import decide_device


class CodeFormulaModelOptions(BaseModel):
    """
    Configuration options for the CodeFormulaModel.

    Attributes
    ----------
    kind : str
        Type of the model. Fixed value "code_formula".
    do_code_enrichment : bool
        True if code enrichment is enabled, False otherwise.
    do_formula_enrichment : bool
        True if formula enrichment is enabled, False otherwise.
    """

    kind: Literal["code_formula"] = "code_formula"
    do_code_enrichment: bool = True
    do_formula_enrichment: bool = True


class CodeFormulaModel(BaseItemAndImageEnrichmentModel):
    """
    Model for processing and enriching documents with code and formula predictions.

    Attributes
    ----------
    enabled : bool
        True if the model is enabled, False otherwise.
    options : CodeFormulaModelOptions
        Configuration options for the CodeFormulaModel.
    code_formula_model : CodeFormulaPredictor
        The predictor model for code and formula processing.

    Methods
    -------
    __init__(self, enabled, artifacts_path, accelerator_options, code_formula_options)
        Initializes the CodeFormulaModel with the given configuration options.
    is_processable(self, doc, element)
        Determines if a given element in a document can be processed by the model.
    __call__(self, doc, element_batch)
        Processes the given batch of elements and enriches them with predictions.
    """

    _model_repo_folder = "ds4sd--CodeFormula"
    elements_batch_size = 5
    images_scale = 1.66  # = 120 dpi, aligned with training data resolution
    expansion_factor = 0.03

    def __init__(
        self,
        enabled: bool,
        artifacts_path: Optional[Path],
        options: CodeFormulaModelOptions,
        accelerator_options: AcceleratorOptions,
    ):
        """
        Initializes the CodeFormulaModel with the given configuration.

        Parameters
        ----------
        enabled : bool
            True if the model is enabled, False otherwise.
        artifacts_path : Path
            Path to the directory containing the model artifacts.
        options : CodeFormulaModelOptions
            Configuration options for the model.
        accelerator_options : AcceleratorOptions
            Options specifying the device and number of threads for acceleration.
        """
        self.enabled = enabled
        self.options = options

        if self.enabled:
            device = decide_device(accelerator_options.device)

            from docling_ibm_models.code_formula_model.code_formula_predictor import (
                CodeFormulaPredictor,
            )

            if artifacts_path is None:
                artifacts_path = self.download_models()
            else:
                artifacts_path = artifacts_path / self._model_repo_folder

            self.code_formula_model = CodeFormulaPredictor(
                artifacts_path=str(artifacts_path),
                device=device,
                num_threads=accelerator_options.num_threads,
            )

    @staticmethod
    def download_models(
        local_dir: Optional[Path] = None,
        force: bool = False,
        progress: bool = False,
    ) -> Path:
        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import disable_progress_bars

        if not progress:
            disable_progress_bars()
        download_path = snapshot_download(
            repo_id="ds4sd/CodeFormula",
            force_download=force,
            local_dir=local_dir,
            revision="v1.0.1",
        )

        return Path(download_path)

    def is_processable(self, doc: DoclingDocument, element: NodeItem) -> bool:
        """
        Determines if a given element in a document can be processed by the model.

        Parameters
        ----------
        doc : DoclingDocument
            The document being processed.
        element : NodeItem
            The element within the document to check.

        Returns
        -------
        bool
            True if the element can be processed, False otherwise.
        """
        return self.enabled and (
            (isinstance(element, CodeItem) and self.options.do_code_enrichment)
            or (
                isinstance(element, TextItem)
                and element.label == DocItemLabel.FORMULA
                and self.options.do_formula_enrichment
            )
        )

    def _extract_code_language(self, input_string: str) -> Tuple[str, Optional[str]]:
        """Extracts a programming language from the beginning of a string.

        This function checks if the input string starts with a pattern of the form
        ``<_some_language_>``. If it does, it extracts the language string and returns
        a tuple of (remainder, language). Otherwise, it returns the original string
        and `None`.

        Args:
            input_string (str): The input string, which may start with ``<_language_>``.

        Returns:
            Tuple[str, Optional[str]]:
                A tuple where:
                - The first element is either:
                    - The remainder of the string (everything after ``<_language_>``),
                    if a match is found; or
                    - The original string, if no match is found.
                - The second element is the extracted language if a match is found;
                otherwise, `None`.
        """
        pattern = r"^<_([^>]+)_>\s*(.*)"
        match = re.match(pattern, input_string, flags=re.DOTALL)
        if match:
            language = str(match.group(1))  # the captured programming language
            remainder = str(match.group(2))  # everything after the <_language_>
            return remainder, language
        else:
            return input_string, None

    def _get_code_language_enum(self, value: Optional[str]) -> CodeLanguageLabel:
        """
        Converts a string to a corresponding `CodeLanguageLabel` enum member.

        If the provided string does not match any value in `CodeLanguageLabel`,
        it defaults to `CodeLanguageLabel.UNKNOWN`.

        Args:
            value (Optional[str]): The string representation of the code language or None.

        Returns:
            CodeLanguageLabel: The corresponding enum member if the value is valid,
            otherwise `CodeLanguageLabel.UNKNOWN`.
        """
        if not isinstance(value, str):
            return CodeLanguageLabel.UNKNOWN

        try:
            return CodeLanguageLabel(value)
        except ValueError:
            return CodeLanguageLabel.UNKNOWN

    def __call__(
        self,
        doc: DoclingDocument,
        element_batch: Iterable[ItemAndImageEnrichmentElement],
    ) -> Iterable[NodeItem]:
        """
        Processes the given batch of elements and enriches them with predictions.

        Parameters
        ----------
        doc : DoclingDocument
            The document being processed.
        element_batch : Iterable[ItemAndImageEnrichmentElement]
            A batch of elements to be processed.

        Returns
        -------
        Iterable[Any]
            An iterable of enriched elements.
        """
        if not self.enabled:
            for element in element_batch:
                yield element.item
            return

        labels: List[str] = []
        images: List[Union[Image.Image, np.ndarray]] = []
        elements: List[TextItem] = []
        for el in element_batch:
            assert isinstance(el.item, TextItem)
            elements.append(el.item)
            labels.append(el.item.label)
            images.append(el.image)

        outputs = self.code_formula_model.predict(images, labels)

        for item, output in zip(elements, outputs):
            if isinstance(item, CodeItem):
                output, code_language = self._extract_code_language(output)
                item.code_language = self._get_code_language_enum(code_language)
            item.text = output

            yield item
