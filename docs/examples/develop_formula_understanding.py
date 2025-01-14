import logging
from pathlib import Path
from typing import Iterable

from docling_core.types.doc import DocItemLabel, DoclingDocument, NodeItem, TextItem
from PIL import Image as PILImage
from pydantic import BaseModel, ConfigDict

from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.models.base_model import BaseEnrichmentModel, GenericEnrichmentModel
from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline


class ExampleFormulaUPipelineOptions(PdfPipelineOptions):
    do_formula_understanding: bool = True


class FormulaEnrichmentElement(BaseModel):
    element: TextItem
    image: PILImage.Image

    model_config = ConfigDict(arbitrary_types_allowed=True)


class ExampleFormulaUEnrichmentModel(GenericEnrichmentModel[FormulaEnrichmentElement]):

    images_scale: float = 2.6

    def __init__(self, enabled: bool):
        self.enabled = enabled

    def is_processable(self, doc: DoclingDocument, element: NodeItem) -> bool:
        return (
            self.enabled
            and isinstance(element, TextItem)
            and element.label == DocItemLabel.FORMULA
        )

    def prepare_element(
        self, conv_res: ConversionResult, element: NodeItem
    ) -> FormulaEnrichmentElement:
        if self.is_processable(doc=conv_res.document, element=element):
            assert isinstance(element, TextItem)
            element_prov = element.prov[0]
            page_ix = element_prov.page_no - 1
            cropped_image = conv_res.pages[page_ix].get_image(
                scale=self.images_scale, cropbox=element_prov.bbox
            )

            return FormulaEnrichmentElement(element=element, image=cropped_image)

    def __call__(
        self, doc: DoclingDocument, element_batch: Iterable[FormulaEnrichmentElement]
    ) -> Iterable[NodeItem]:
        if not self.enabled:
            return

        for enrich_element in element_batch:
            enrich_element.image.show()

            yield enrich_element.element


# How the pipeline can be extended.
class ExampleFormulaUPipeline(StandardPdfPipeline):

    def __init__(self, pipeline_options: ExampleFormulaUPipelineOptions):
        super().__init__(pipeline_options)
        self.pipeline_options: ExampleFormulaUPipelineOptions

        self.enrichment_pipe = [
            ExampleFormulaUEnrichmentModel(
                enabled=self.pipeline_options.do_formula_understanding
            )
        ]

        if self.pipeline_options.do_formula_understanding:
            self.keep_backend = True

    @classmethod
    def get_default_options(cls) -> ExampleFormulaUPipelineOptions:
        return ExampleFormulaUPipelineOptions()


# Example main. In the final version, we simply have to set do_formula_understanding to true.
def main():
    logging.basicConfig(level=logging.INFO)

    input_doc_path = Path("./tests/data/2203.01017v2.pdf")

    pipeline_options = ExampleFormulaUPipelineOptions()
    pipeline_options.do_formula_understanding = True

    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_cls=ExampleFormulaUPipeline,
                pipeline_options=pipeline_options,
            )
        }
    )
    result = doc_converter.convert(input_doc_path)


if __name__ == "__main__":
    main()
