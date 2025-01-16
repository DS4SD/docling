import itertools
import logging
import re
from io import BytesIO
from pathlib import Path
from typing import Optional

from docling_core.types import DoclingDocument
from docling_core.types.doc import (
    BoundingBox,
    DocItem,
    DocItemLabel,
    DoclingDocument,
    GroupLabel,
    ImageRef,
    ImageRefMode,
    PictureItem,
    ProvenanceItem,
    Size,
    TableCell,
    TableData,
    TableItem,
)
from docling_core.types.doc.tokens import DocumentToken, TableToken

from docling.backend.abstract_backend import AbstractDocumentBackend
from docling.backend.pdf_backend import PdfDocumentBackend
from docling.datamodel.base_models import Page
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.models.smol_docling_model import SmolDoclingModel
from docling.pipeline.base_pipeline import PaginatedPipeline
from docling.utils.profiling import ProfilingScope, TimeRecorder

_log = logging.getLogger(__name__)


class VlmPipeline(PaginatedPipeline):
    _smol_vlm_path = "SmolDocling-0.0.2"

    def __init__(self, pipeline_options: PdfPipelineOptions):
        super().__init__(pipeline_options)
        self.pipeline_options: PdfPipelineOptions

        # force_backend_text = False - use text that is coming from SmolDocling
        # force_backend_text = True - get text from backend using bounding boxes predicted by SmolDoclingss
        self.force_backend_text = pipeline_options.force_backend_text

        if pipeline_options.artifacts_path is None:
            self.artifacts_path = self.download_models_hf()
        else:
            self.artifacts_path = Path(pipeline_options.artifacts_path)

        keep_images = (
            self.pipeline_options.generate_page_images
            or self.pipeline_options.generate_picture_images
            or self.pipeline_options.generate_table_images
        )

        self.build_pipe = [
            SmolDoclingModel(
                artifacts_path=self.artifacts_path / VlmPipeline._smol_vlm_path,
                accelerator_options=pipeline_options.accelerator_options,
            ),
        ]

        self.enrichment_pipe = [
            # Other models working on `NodeItem` elements in the DoclingDocument
        ]

    @staticmethod
    def download_models_hf(
        local_dir: Optional[Path] = None, force: bool = False
    ) -> Path:
        from huggingface_hub import snapshot_download
        from huggingface_hub.utils import disable_progress_bars

        disable_progress_bars()

        # TODO: download the correct model (private repo)
        download_path = snapshot_download(
            repo_id="ds4sd/xxx",
            force_download=force,
            local_dir=local_dir,
        )

        return Path(download_path)

    def initialize_page(self, conv_res: ConversionResult, page: Page) -> Page:
        with TimeRecorder(conv_res, "page_init"):
            page._backend = conv_res.input._backend.load_page(page.page_no)  # type: ignore
            if page._backend is not None and page._backend.is_valid():
                page.size = page._backend.get_size()

        return page

    def _assemble_document(self, conv_res: ConversionResult) -> ConversionResult:
        with TimeRecorder(conv_res, "doc_assemble", scope=ProfilingScope.DOCUMENT):

            conv_res.document = self._turn_tags_into_doc(conv_res.pages)

            # Generate images of the requested element types
            if (
                self.pipeline_options.generate_picture_images
                or self.pipeline_options.generate_table_images
            ):
                scale = self.pipeline_options.images_scale
                for element, _level in conv_res.document.iterate_items():
                    if not isinstance(element, DocItem) or len(element.prov) == 0:
                        continue
                    if (
                        isinstance(element, PictureItem)
                        and self.pipeline_options.generate_picture_images
                    ) or (
                        isinstance(element, TableItem)
                        and self.pipeline_options.generate_table_images
                    ):
                        page_ix = element.prov[0].page_no - 1
                        page = conv_res.pages[page_ix]
                        assert page.size is not None
                        assert page.image is not None

                        crop_bbox = (
                            element.prov[0]
                            .bbox.scaled(scale=scale)
                            .to_top_left_origin(page_height=page.size.height * scale)
                        )

                        cropped_im = page.image.crop(crop_bbox.as_tuple())
                        element.image = ImageRef.from_pil(
                            cropped_im, dpi=int(72 * scale)
                        )

        return conv_res

    def _turn_tags_into_doc(self, pages: list[Page]) -> DoclingDocument:

        def extract_text_from_backend(page: Page, bbox: BoundingBox | None) -> str:
            # Convert bounding box normalized to 0-100 into page coordinates for cropping
            text = ""
            if bbox:
                if page.size:
                    bbox.l = bbox.l * page.size.width
                    bbox.t = bbox.t * page.size.height
                    bbox.r = bbox.r * page.size.width
                    bbox.b = bbox.b * page.size.height
                    if page._backend:
                        text = page._backend.get_text_in_rect(bbox)
            return text

        def extract_text(tag_content: str) -> str:
            return re.sub(r"<.*?>", "", tag_content).strip()

        def extract_bounding_box(tag_content: str) -> Optional[BoundingBox]:
            locs = re.findall(r"<loc_(\d+)>", tag_content)
            if len(locs) == 4:
                l, t, r, b = map(float, locs)
                l, t, r, b = [coord / 500.0 for coord in (l, t, r, b)]
                return BoundingBox(l=l, t=t, r=r, b=b)
            return None

        def parse_texts(texts, tokens):
            split_word = TableToken.OTSL_NL.value
            split_row_tokens = [
                list(y)
                for x, y in itertools.groupby(tokens, lambda z: z == split_word)
                if not x
            ]
            table_cells = []
            r_idx = 0
            c_idx = 0

            def count_right(tokens, c_idx, r_idx, which_tokens):
                span = 0
                c_idx_iter = c_idx
                while tokens[r_idx][c_idx_iter] in which_tokens:
                    c_idx_iter += 1
                    span += 1
                    if c_idx_iter >= len(tokens[r_idx]):
                        return span
                return span

            def count_down(tokens, c_idx, r_idx, which_tokens):
                span = 0
                r_idx_iter = r_idx
                while tokens[r_idx_iter][c_idx] in which_tokens:
                    r_idx_iter += 1
                    span += 1
                    if r_idx_iter >= len(tokens):
                        return span
                return span

            for i, text in enumerate(texts):
                cell_text = ""
                if text in [
                    TableToken.OTSL_FCEL.value,
                    TableToken.OTSL_ECEL.value,
                    TableToken.OTSL_CHED.value,
                    TableToken.OTSL_RHED.value,
                    TableToken.OTSL_SROW.value,
                ]:
                    row_span = 1
                    col_span = 1
                    right_offset = 1
                    if text != TableToken.OTSL_ECEL.value:
                        cell_text = texts[i + 1]
                        right_offset = 2

                    # Check next element(s) for lcel / ucel / xcel, set properly row_span, col_span
                    next_right_cell = texts[i + right_offset]

                    next_bottom_cell = ""
                    if r_idx + 1 < len(split_row_tokens):
                        if c_idx < len(split_row_tokens[r_idx + 1]):
                            next_bottom_cell = split_row_tokens[r_idx + 1][c_idx]

                    if next_right_cell in [
                        TableToken.OTSL_LCEL.value,
                        TableToken.OTSL_XCEL.value,
                    ]:
                        # we have horisontal spanning cell or 2d spanning cell
                        col_span += count_right(
                            split_row_tokens,
                            c_idx + 1,
                            r_idx,
                            [TableToken.OTSL_LCEL.value, TableToken.OTSL_XCEL.value],
                        )
                    if next_bottom_cell in [
                        TableToken.OTSL_UCEL.value,
                        TableToken.OTSL_XCEL.value,
                    ]:
                        # we have a vertical spanning cell or 2d spanning cell
                        row_span += count_down(
                            split_row_tokens,
                            c_idx,
                            r_idx + 1,
                            [TableToken.OTSL_UCEL.value, TableToken.OTSL_XCEL.value],
                        )

                    table_cells.append(
                        TableCell(
                            text=cell_text.strip(),
                            row_span=row_span,
                            col_span=col_span,
                            start_row_offset_idx=r_idx,
                            end_row_offset_idx=r_idx + row_span,
                            start_col_offset_idx=c_idx,
                            end_col_offset_idx=c_idx + col_span,
                        )
                    )
                if text in [
                    TableToken.OTSL_FCEL.value,
                    TableToken.OTSL_ECEL.value,
                    TableToken.OTSL_CHED.value,
                    TableToken.OTSL_RHED.value,
                    TableToken.OTSL_SROW.value,
                    TableToken.OTSL_LCEL.value,
                    TableToken.OTSL_UCEL.value,
                    TableToken.OTSL_XCEL.value,
                ]:
                    c_idx += 1
                if text == TableToken.OTSL_NL.value:
                    r_idx += 1
                    c_idx = 0
            return table_cells, split_row_tokens

        def extract_tokens_and_text(s: str):
            # Pattern to match anything enclosed by < > (including the angle brackets themselves)
            pattern = r"(<[^>]+>)"
            # Find all tokens (e.g. "<otsl>", "<loc_140>", etc.)
            tokens = re.findall(pattern, s)
            # Remove any tokens that start with "<loc_"
            tokens = [
                token
                for token in tokens
                if not (token.startswith("<loc_") or token in ["<otsl>", "</otsl>"])
            ]
            # Split the string by those tokens to get the in-between text
            text_parts = re.split(pattern, s)
            text_parts = [
                token
                for token in text_parts
                if not (token.startswith("<loc_") or token in ["<otsl>", "</otsl>"])
            ]
            # Remove any empty or purely whitespace strings from text_parts
            text_parts = [part for part in text_parts if part.strip()]

            return tokens, text_parts

        def parse_table_content(otsl_content: str) -> TableData:
            tokens, mixed_texts = extract_tokens_and_text(otsl_content)
            table_cells, split_row_tokens = parse_texts(mixed_texts, tokens)

            return TableData(
                num_rows=len(split_row_tokens),
                num_cols=(
                    max(len(row) for row in split_row_tokens) if split_row_tokens else 0
                ),
                table_cells=table_cells,
            )

        doc = DoclingDocument(name="Example Document")
        current_group = None

        for pg_idx, page in enumerate(pages):
            xml_content = ""
            if page.predictions.doctags:
                xml_content = page.predictions.doctags.tag_string
            pil_image = page.image
            page_no = pg_idx + 1

            if page.size:
                pg_width = page.size.width
                pg_height = page.size.height
                size = Size(width=pg_width, height=pg_height)
                parent_page = doc.add_page(page_no=page_no, size=size)

            lines = xml_content.split("\n")
            bounding_boxes = []

            for line in lines:
                line = line.strip()
                line = line.replace("<doc_tag>", "")
                if line.startswith("<paragraph>"):
                    prov_item = extract_bounding_box(line)
                    if self.force_backend_text:
                        content = extract_text_from_backend(page, prov_item)
                    else:
                        content = extract_text(line)

                    if prov_item:
                        bounding_boxes.append((prov_item, "red"))
                    doc.add_text(
                        label=DocItemLabel.PARAGRAPH,
                        text=content,
                        parent=current_group,
                        prov=(
                            ProvenanceItem(
                                bbox=prov_item, charspan=(0, 0), page_no=page_no
                            )
                            if prov_item
                            else None
                        ),
                    )
                elif line.startswith("<title>"):
                    prov_item = extract_bounding_box(line)
                    if self.force_backend_text:
                        content = extract_text_from_backend(page, prov_item)
                    else:
                        content = extract_text(line)

                    if prov_item:
                        bounding_boxes.append((prov_item, "blue"))
                    current_group = doc.add_group(
                        label=GroupLabel.SECTION, name=content
                    )
                    doc.add_text(
                        label=DocItemLabel.TITLE,
                        text=content,
                        parent=current_group,
                        prov=(
                            ProvenanceItem(
                                bbox=prov_item, charspan=(0, 0), page_no=page_no
                            )
                            if prov_item
                            else None
                        ),
                    )

                elif line.startswith("<section-header>"):
                    prov_item = extract_bounding_box(line)
                    if self.force_backend_text:
                        content = extract_text_from_backend(page, prov_item)
                    else:
                        content = extract_text(line)

                    if prov_item:
                        bounding_boxes.append((prov_item, "green"))
                    current_group = doc.add_group(
                        label=GroupLabel.SECTION, name=content
                    )
                    doc.add_text(
                        label=DocItemLabel.SECTION_HEADER,
                        text=content,
                        parent=current_group,
                        prov=(
                            ProvenanceItem(
                                bbox=prov_item, charspan=(0, 0), page_no=page_no
                            )
                            if prov_item
                            else None
                        ),
                    )

                elif line.startswith("<otsl>"):
                    prov_item = extract_bounding_box(line)
                    if prov_item:
                        bounding_boxes.append((prov_item, "aquamarine"))

                    table_data = parse_table_content(line)
                    doc.add_table(data=table_data, parent=current_group)

                elif line.startswith("<footnote>"):
                    prov_item = extract_bounding_box(line)
                    if self.force_backend_text:
                        content = extract_text_from_backend(page, prov_item)
                    else:
                        content = extract_text(line)
                    if prov_item:
                        bounding_boxes.append((prov_item, "orange"))
                    doc.add_text(
                        label=DocItemLabel.FOOTNOTE,
                        text=content,
                        parent=current_group,
                        prov=(
                            ProvenanceItem(
                                bbox=prov_item, charspan=(0, 0), page_no=page_no
                            )
                            if prov_item
                            else None
                        ),
                    )

                elif line.startswith("<page-header>"):
                    prov_item = extract_bounding_box(line)
                    if self.force_backend_text:
                        content = extract_text_from_backend(page, prov_item)
                    else:
                        content = extract_text(line)
                    if prov_item:
                        bounding_boxes.append((prov_item, "purple"))
                    doc.add_text(
                        label=DocItemLabel.PAGE_HEADER,
                        text=content,
                        parent=current_group,
                        prov=(
                            ProvenanceItem(
                                bbox=prov_item, charspan=(0, 0), page_no=page_no
                            )
                            if prov_item
                            else None
                        ),
                    )

                elif line.startswith("<page-footer>"):
                    prov_item = extract_bounding_box(line)
                    if self.force_backend_text:
                        content = extract_text_from_backend(page, prov_item)
                    else:
                        content = extract_text(line)
                    if prov_item:
                        bounding_boxes.append((prov_item, "cyan"))
                    doc.add_text(
                        label=DocItemLabel.PAGE_FOOTER,
                        text=content,
                        parent=current_group,
                        prov=(
                            ProvenanceItem(
                                bbox=prov_item, charspan=(0, 0), page_no=page_no
                            )
                            if prov_item
                            else None
                        ),
                    )

                elif line.startswith("<figure>"):
                    bbox = extract_bounding_box(line)
                    if bbox:
                        bounding_boxes.append((bbox, "yellow"))
                        if pil_image:
                            # Convert bounding box normalized to 0-100 into pixel coordinates for cropping
                            width, height = pil_image.size
                            crop_box = (
                                int(bbox.l * width),
                                int(bbox.t * height),
                                int(bbox.r * width),
                                int(bbox.b * height),
                            )

                            cropped_image = pil_image.crop(crop_box)
                            doc.add_picture(
                                parent=current_group,
                                image=ImageRef.from_pil(image=cropped_image, dpi=300),
                                prov=ProvenanceItem(
                                    bbox=bbox, charspan=(0, 0), page_no=page_no
                                ),
                            )
                        else:
                            doc.add_picture(
                                parent=current_group,
                                prov=ProvenanceItem(
                                    bbox=bbox, charspan=(0, 0), page_no=page_no
                                ),
                            )
                elif line.startswith("<list>"):
                    prov_item_inst = None
                    prov_item = extract_bounding_box(line)
                    if self.force_backend_text:
                        content = extract_text_from_backend(page, prov_item)
                    else:
                        content = extract_text(line)
                    if prov_item:
                        bounding_boxes.append((prov_item, "brown"))
                        prov_item_inst = ProvenanceItem(
                            bbox=prov_item, charspan=(0, 0), page_no=page_no
                        )
                    doc.add_text(
                        label=DocItemLabel.LIST_ITEM,
                        text=content,
                        parent=current_group,
                        prov=prov_item_inst if prov_item_inst else None,
                    )

                elif line.startswith("<caption>"):
                    prov_item_inst = None
                    prov_item = extract_bounding_box(line)
                    if self.force_backend_text:
                        content = extract_text_from_backend(page, prov_item)
                    else:
                        content = extract_text(line)
                    if prov_item:
                        bounding_boxes.append((prov_item, "magenta"))
                        prov_item_inst = ProvenanceItem(
                            bbox=prov_item, charspan=(0, 0), page_no=page_no
                        )
                    doc.add_text(
                        label=DocItemLabel.PARAGRAPH,
                        text=content,
                        parent=current_group,
                        prov=prov_item_inst if prov_item_inst else None,
                    )
                elif line.startswith("<checkbox-unselected>"):
                    prov_item_inst = None
                    prov_item = extract_bounding_box(line)
                    if self.force_backend_text:
                        content = extract_text_from_backend(page, prov_item)
                    else:
                        content = extract_text(line)
                    if prov_item:
                        bounding_boxes.append((prov_item, "gray"))
                        prov_item_inst = ProvenanceItem(
                            bbox=prov_item, charspan=(0, 0), page_no=page_no
                        )
                    doc.add_text(
                        label=DocItemLabel.CHECKBOX_UNSELECTED,
                        text=content,
                        parent=current_group,
                        prov=prov_item_inst if prov_item_inst else None,
                    )

                elif line.startswith("<checkbox-selected>"):
                    prov_item_inst = None
                    prov_item = extract_bounding_box(line)
                    if self.force_backend_text:
                        content = extract_text_from_backend(page, prov_item)
                    else:
                        content = extract_text(line)
                    if prov_item:
                        bounding_boxes.append((prov_item, "black"))
                        prov_item_inst = ProvenanceItem(
                            bbox=prov_item, charspan=(0, 0), page_no=page_no
                        )
                    doc.add_text(
                        label=DocItemLabel.CHECKBOX_SELECTED,
                        text=content,
                        parent=current_group,
                        prov=prov_item_inst if prov_item_inst else None,
                    )
            # return doc, bounding_boxes
        return doc

    @classmethod
    def get_default_options(cls) -> PdfPipelineOptions:
        return PdfPipelineOptions()

    @classmethod
    def is_backend_supported(cls, backend: AbstractDocumentBackend):
        return isinstance(backend, PdfDocumentBackend)

    # def _turn_tags_into_doc(self, document_tags):
    #     return DoclingDocument()
