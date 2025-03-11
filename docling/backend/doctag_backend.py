import logging
from abc import ABC, abstractmethod
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Set, Union

from docling_core.types.doc import DoclingDocument
from docling.backend.abstract_backend import DeclarativeDocumentBackend

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

if TYPE_CHECKING:
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.document import InputDocument

_log = logging.getLogger(__name__)


class DoctagDocumentBackend(DeclarativeDocumentBackend):
    """DoctagDocumentBackend.

    Transforms Doctags to DoclingDocument
    """

    def _turn_tags_into_doc(self, pages: list[Page]) -> DoclingDocument:
        ###############################################
        # Tag definitions and color mappings
        ###############################################

        # Maps the recognized tag to a Docling label.
        # Code items will be given DocItemLabel.CODE
        tag_to_doclabel = {
            "title": DocItemLabel.TITLE,
            "document_index": DocItemLabel.DOCUMENT_INDEX,
            "otsl": DocItemLabel.TABLE,
            "section_header_level_1": DocItemLabel.SECTION_HEADER,
            "checkbox_selected": DocItemLabel.CHECKBOX_SELECTED,
            "checkbox_unselected": DocItemLabel.CHECKBOX_UNSELECTED,
            "text": DocItemLabel.TEXT,
            "page_header": DocItemLabel.PAGE_HEADER,
            "page_footer": DocItemLabel.PAGE_FOOTER,
            "formula": DocItemLabel.FORMULA,
            "caption": DocItemLabel.CAPTION,
            "picture": DocItemLabel.PICTURE,
            "list_item": DocItemLabel.LIST_ITEM,
            "footnote": DocItemLabel.FOOTNOTE,
            "code": DocItemLabel.CODE,
        }

        # Maps each tag to an associated bounding box color.
        tag_to_color = {
            "title": "blue",
            "document_index": "darkblue",
            "otsl": "green",
            "section_header_level_1": "purple",
            "checkbox_selected": "black",
            "checkbox_unselected": "gray",
            "text": "red",
            "page_header": "orange",
            "page_footer": "cyan",
            "formula": "pink",
            "caption": "magenta",
            "picture": "yellow",
            "list_item": "brown",
            "footnote": "darkred",
            "code": "lightblue",
        }

        def extract_bounding_box(text_chunk: str) -> Optional[BoundingBox]:
            """Extracts <loc_...> bounding box coords from the chunk, normalized by / 500."""
            coords = re.findall(r"<loc_(\d+)>", text_chunk)
            if len(coords) == 4:
                l, t, r, b = map(float, coords)
                return BoundingBox(l=l / 500, t=t / 500, r=r / 500, b=b / 500)
            return None

        def extract_inner_text(text_chunk: str) -> str:
            """Strips all <...> tags inside the chunk to get the raw text content."""
            return re.sub(r"<.*?>", "", text_chunk, flags=re.DOTALL).strip()

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

        def otsl_parse_texts(texts, tokens):
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
                    next_right_cell = ""
                    if i + right_offset < len(texts):
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

        def otsl_extract_tokens_and_text(s: str):
            # Pattern to match anything enclosed by < > (including the angle brackets themselves)
            pattern = r"(<[^>]+>)"
            # Find all tokens (e.g. "<otsl>", "<loc_140>", etc.)
            tokens = re.findall(pattern, s)
            # Remove any tokens that start with "<loc_"
            tokens = [
                token
                for token in tokens
                if not (
                    token.startswith(rf"<{DocumentToken.LOC.value}")
                    or token
                    in [
                        rf"<{DocumentToken.OTSL.value}>",
                        rf"</{DocumentToken.OTSL.value}>",
                    ]
                )
            ]
            # Split the string by those tokens to get the in-between text
            text_parts = re.split(pattern, s)
            text_parts = [
                token
                for token in text_parts
                if not (
                    token.startswith(rf"<{DocumentToken.LOC.value}")
                    or token
                    in [
                        rf"<{DocumentToken.OTSL.value}>",
                        rf"</{DocumentToken.OTSL.value}>",
                    ]
                )
            ]
            # Remove any empty or purely whitespace strings from text_parts
            text_parts = [part for part in text_parts if part.strip()]

            return tokens, text_parts

        def parse_table_content(otsl_content: str) -> TableData:
            tokens, mixed_texts = otsl_extract_tokens_and_text(otsl_content)
            table_cells, split_row_tokens = otsl_parse_texts(mixed_texts, tokens)

            return TableData(
                num_rows=len(split_row_tokens),
                num_cols=(
                    max(len(row) for row in split_row_tokens) if split_row_tokens else 0
                ),
                table_cells=table_cells,
            )

        doc = DoclingDocument(name="Document")
        for pg_idx, page in enumerate(pages):
            xml_content = ""
            predicted_text = ""
            if page.predictions.vlm_response:
                predicted_text = page.predictions.vlm_response.text
            image = page.image

            page_no = pg_idx + 1
            bounding_boxes = []

            if page.size:
                pg_width = page.size.width
                pg_height = page.size.height
                size = Size(width=pg_width, height=pg_height)
                parent_page = doc.add_page(page_no=page_no, size=size)

            """
            1. Finds all <tag>...</tag> blocks in the entire string (multi-line friendly) in the order they appear.
            2. For each chunk, extracts bounding box (if any) and inner text.
            3. Adds the item to a DoclingDocument structure with the right label.
            4. Tracks bounding boxes + color in a separate list for later visualization.
            """

            # Regex for all recognized tags
            tag_pattern = (
                rf"<(?P<tag>{DocItemLabel.TITLE}|{DocItemLabel.DOCUMENT_INDEX}|"
                rf"{DocItemLabel.CHECKBOX_UNSELECTED}|{DocItemLabel.CHECKBOX_SELECTED}|"
                rf"{DocItemLabel.TEXT}|{DocItemLabel.PAGE_HEADER}|"
                rf"{DocItemLabel.PAGE_FOOTER}|{DocItemLabel.FORMULA}|"
                rf"{DocItemLabel.CAPTION}|{DocItemLabel.PICTURE}|"
                rf"{DocItemLabel.LIST_ITEM}|{DocItemLabel.FOOTNOTE}|{DocItemLabel.CODE}|"
                rf"{DocItemLabel.SECTION_HEADER}_level_1|{DocumentToken.OTSL.value})>.*?</(?P=tag)>"
            )

            # DocumentToken.OTSL
            pattern = re.compile(tag_pattern, re.DOTALL)

            # Go through each match in order
            for match in pattern.finditer(predicted_text):
                full_chunk = match.group(0)
                tag_name = match.group("tag")

                bbox = extract_bounding_box(full_chunk)
                doc_label = tag_to_doclabel.get(tag_name, DocItemLabel.PARAGRAPH)
                color = tag_to_color.get(tag_name, "white")

                # Store bounding box + color
                if bbox:
                    bounding_boxes.append((bbox, color))

                if tag_name == DocumentToken.OTSL.value:
                    table_data = parse_table_content(full_chunk)
                    bbox = extract_bounding_box(full_chunk)

                    if bbox:
                        prov = ProvenanceItem(
                            bbox=bbox.resize_by_scale(pg_width, pg_height),
                            charspan=(0, 0),
                            page_no=page_no,
                        )
                        doc.add_table(data=table_data, prov=prov)
                    else:
                        doc.add_table(data=table_data)

                elif tag_name == DocItemLabel.PICTURE:
                    text_caption_content = extract_inner_text(full_chunk)
                    if image:
                        if bbox:
                            im_width, im_height = image.size

                            crop_box = (
                                int(bbox.l * im_width),
                                int(bbox.t * im_height),
                                int(bbox.r * im_width),
                                int(bbox.b * im_height),
                            )
                            cropped_image = image.crop(crop_box)
                            pic = doc.add_picture(
                                parent=None,
                                image=ImageRef.from_pil(image=cropped_image, dpi=72),
                                prov=(
                                    ProvenanceItem(
                                        bbox=bbox.resize_by_scale(pg_width, pg_height),
                                        charspan=(0, 0),
                                        page_no=page_no,
                                    )
                                ),
                            )
                            # If there is a caption to an image, add it as well
                            if len(text_caption_content) > 0:
                                caption_item = doc.add_text(
                                    label=DocItemLabel.CAPTION,
                                    text=text_caption_content,
                                    parent=None,
                                )
                                pic.captions.append(caption_item.get_ref())
                    else:
                        if bbox:
                            # In case we don't have access to an binary of an image
                            doc.add_picture(
                                parent=None,
                                prov=ProvenanceItem(
                                    bbox=bbox, charspan=(0, 0), page_no=page_no
                                ),
                            )
                            # If there is a caption to an image, add it as well
                            if len(text_caption_content) > 0:
                                caption_item = doc.add_text(
                                    label=DocItemLabel.CAPTION,
                                    text=text_caption_content,
                                    parent=None,
                                )
                                pic.captions.append(caption_item.get_ref())
                else:
                    # For everything else, treat as text
                    if self.force_backend_text:
                        text_content = extract_text_from_backend(page, bbox)
                    else:
                        text_content = extract_inner_text(full_chunk)
                    doc.add_text(
                        label=doc_label,
                        text=text_content,
                        prov=(
                            ProvenanceItem(
                                bbox=bbox.resize_by_scale(pg_width, pg_height),
                                charspan=(0, len(text_content)),
                                page_no=page_no,
                            )
                            if bbox
                            else None
                        ),
                    )
        return doc


    def __init__(self, in_doc: "InputDocument", path_or_stream: Union[BytesIO, Path]):
        def _clean_doctags(txt):
            return txt

        super().__init__(in_doc, path_or_stream)

        _log.debug("Doctag backend INIT!!!")

        # Doctag file:
        self.path_or_stream = path_or_stream
        self.valid = True
        self.doctag = ""  # To store original Doctag string

        try:
            if isinstance(self.path_or_stream, BytesIO):
                text_stream = self.path_or_stream.getvalue().decode("utf-8")
                self.doctag = self._clean_doctags(text_stream)
            if isinstance(self.path_or_stream, Path):
                with open(self.path_or_stream, "r", encoding="utf-8") as f:
                    doctag_content = f.read()
                    # remove invalid sequences
                    self.markdown = self._clean_doctags(doctag_content)
            self.valid = True

            _log.debug(self.doctag)
        except Exception as e:
            raise RuntimeError(
                f"Could not initialize DocTag backend for file with hash {self.document_hash}."
            ) from e
        return

    def is_valid(self) -> bool:
        return self.valid

    @classmethod
    def supports_pagination(cls) -> bool:
        return True

    @classmethod
    def supported_formats(cls) -> Set[InputFormat]:
        return {InputFormat.DOCTAG}

    @abstractmethod
    def convert(self) -> DoclingDocument:
        _log.debug("converting DocTags...")

        origin = DocumentOrigin(
            filename=self.file.name or "file",
            mimetype="text",
            binary_hash=self.document_hash,
        )

        doc = DoclingDocument(name=self.file.stem or "file", origin=origin)
        doc = self._turn_tags_into_doc(self.doctag, doc)

        return doc
