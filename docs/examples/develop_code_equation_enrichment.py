import logging
from pathlib import Path
from typing import Any, Iterable, Literal

from docling_core.types.doc import (
    DoclingDocument,
    NodeItem,
    TextItem,
)
from enum import Enum

from pydantic import BaseModel

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import AcceleratorOptions, PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.models.base_model import BaseEnrichmentModel
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline

from docling_ibm_models.code_formula_model.code_formula_predictor import (
    CodeFormulaPredictor,
)

from docling.datamodel.settings import settings

# TODO: remove this. Imported so that the models are registered
from docling_ibm_models.code_formula_model.models.vary_opt import *
from docling_ibm_models.code_formula_model.models.vary_opt_image_processor import *


class CodeFormulaMode(str, Enum):
    """Modes for the CodeFormula model."""

    CODE = "code"
    FORMULA = "formula"
    CODE_FORMULA = "code_formula"


class CodeFormulaModelOptions(BaseModel):
    kind: Literal["code_formula"] = "code_formula"

    mode: CodeFormulaMode = CodeFormulaMode.CODE_FORMULA


class CodeFormulaModel(BaseEnrichmentModel):

    def __init__(
        self,
        enabled: bool,
        artifacts_path: Path,
        accelerator_options: AcceleratorOptions,
        code_formula_options: CodeFormulaModelOptions,
    ):
        """Init the CodeFormulaModel.

        Args:
            enabled (bool): True if the model is enabled, False othewise.
            
        """
        self.enabled = enabled
        self.mode = code_formula_options.mode

        self.code_formula_model = CodeFormulaPredictor(
            artifacts_path=artifacts_path,
            device=accelerator_options.device,
            num_threads=accelerator_options.num_threads,
        )

    def is_processable(self, doc: DoclingDocument, element: NodeItem) -> bool:
        return (
            self.enabled
            and isinstance(element, TextItem)
            and (
                (
                    element.label == "code"
                    and (
                        CodeFormulaMode.CODE
                        or self.mode == CodeFormulaMode.CODE_FORMULA
                    )
                )
                or (
                    element.label == "formula"
                    and (
                        self.mode == CodeFormulaMode.FORMULA
                        or self.mode == CodeFormulaMode.CODE_FORMULA
                    )
                )
            )
        )

    def __call__(
        self, doc: DoclingDocument, element_batch: Iterable[NodeItem]
    ) -> Iterable[Any]:
        print(len(element_batch))
        if not self.enabled:
            return

        # ! TODO: batch size missing
        images = [el.get_image(doc) for el in element_batch]
        labels = [el.label for el in element_batch]
        
        outputs = self.code_formula_model.predict(images, labels)
        # for output in outputs:
        #     print(output)
        #     print("\n\n\n\n\n")

        for element, output in zip(element_batch, outputs):
            element.text = output

        yield element_batch


class CodeFormulaPipelineOptions(PdfPipelineOptions):
    do_code_formula_enrichment: bool = True

class CodeFormulaPipeline(StandardPdfPipeline):

    def __init__(self, pipeline_options: CodeFormulaPipelineOptions):
        super().__init__(pipeline_options)
        self.pipeline_options: CodeFormulaPipelineOptions

        self.enrichment_pipe = [
            CodeFormulaModel(
                enabled=pipeline_options.do_code_formula_enrichment,
                artifacts_path="/dccstor/doc_fig_class/DocFM-Vision-Pretrainer/Vary-master/checkpoints_code_equation_model/best_run",
                accelerator_options=AcceleratorOptions(device="cpu"),
                code_formula_options=CodeFormulaModelOptions(),
            )
        ]

    @classmethod
    def get_default_options(cls) -> CodeFormulaPipelineOptions:
        return CodeFormulaPipelineOptions()


def main():
    logging.basicConfig(level=logging.INFO)

    # input_doc_path = Path("./tests/data/code_and_formulas.pdf")
    input_doc_path = Path(
        "/dccstor/doc_fig_class/docling-ibm/test/data/pdf/code_and_formulas.pdf"
    )

    settings.debug.visualize_raw_layout = True
    settings.debug.visualize_layout = True
    settings.debug.visualize_ocr = True
    settings.debug.visualize_tables = True

    pipeline_options = CodeFormulaPipelineOptions()
    pipeline_options.images_scale = 2.0

    pipeline_options.generate_page_images = True
    pipeline_options.generate_picture_images = True

    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_cls=CodeFormulaPipeline,
                pipeline_options=pipeline_options,
            )
        }
    )
    result = doc_converter.convert(input_doc_path)

    for element, _level in result.document.iterate_items():
        if isinstance(element, TextItem) and (element.label == "code" or element.label == "formula"):
            print(
                f"The model populated the `text` portion of the TextElement {element.self_ref}:\n{element.text}\n\n\n\n\n"
            )


if __name__ == "__main__":
    main()
