import logging
import re
from io import BytesIO
from pathlib import Path
from typing import Set, Union

import docx
from docling_core.types.doc import (
    DocItemLabel,
    DoclingDocument,
    DocumentOrigin,
    GroupLabel,
    ImageRef,
    TableCell,
    TableData,
)
from lxml import etree
from lxml.etree import XPath
from PIL import Image, UnidentifiedImageError

from docling.backend.abstract_backend import DeclarativeDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import InputDocument

_log = logging.getLogger(__name__)


class MsWordDocumentBackend(DeclarativeDocumentBackend):

    def __init__(self, in_doc: "InputDocument", path_or_stream: Union[BytesIO, Path]):
        super().__init__(in_doc, path_or_stream)
        self.XML_KEY = (
            "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val"
        )
        self.xml_namespaces = {
            "w": "http://schemas.microsoft.com/office/word/2003/wordml"
        }
        # self.initialise(path_or_stream)
        # Word file:
        self.path_or_stream = path_or_stream
        self.valid = False
        # Initialise the parents for the hierarchy
        self.max_levels = 10
        self.level_at_new_list = None
        self.parents = {}  # type: ignore
        for i in range(-1, self.max_levels):
            self.parents[i] = None

        self.level = 0
        self.listIter = 0

        self.history = {
            "names": [None],
            "levels": [None],
            "numids": [None],
            "indents": [None],
        }

        self.docx_obj = None
        try:
            if isinstance(self.path_or_stream, BytesIO):
                self.docx_obj = docx.Document(self.path_or_stream)
            elif isinstance(self.path_or_stream, Path):
                self.docx_obj = docx.Document(str(self.path_or_stream))

            self.valid = True
        except Exception as e:
            raise RuntimeError(
                f"MsPowerpointDocumentBackend could not load document with hash {self.document_hash}"
            ) from e

    def is_valid(self) -> bool:
        return self.valid

    @classmethod
    def supports_pagination(cls) -> bool:
        return False

    def unload(self):
        if isinstance(self.path_or_stream, BytesIO):
            self.path_or_stream.close()

        self.path_or_stream = None

    @classmethod
    def supported_formats(cls) -> Set[InputFormat]:
        return {InputFormat.DOCX}

    def convert(self) -> DoclingDocument:
        # Parses the DOCX into a structured document model.

        origin = DocumentOrigin(
            filename=self.file.name or "file",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            binary_hash=self.document_hash,
        )

        doc = DoclingDocument(name=self.file.stem or "file", origin=origin)
        if self.is_valid():
            assert self.docx_obj is not None
            doc = self.walk_linear(self.docx_obj.element.body, self.docx_obj, doc)
            return doc
        else:
            raise RuntimeError(
                f"Cannot convert doc with {self.document_hash} because the backend failed to init."
            )

    def update_history(self, name, level, numid, ilevel):
        self.history["names"].append(name)
        self.history["levels"].append(level)

        self.history["numids"].append(numid)
        self.history["indents"].append(ilevel)

    def prev_name(self):
        return self.history["names"][-1]

    def prev_level(self):
        return self.history["levels"][-1]

    def prev_numid(self):
        return self.history["numids"][-1]

    def prev_indent(self):
        return self.history["indents"][-1]

    def get_level(self) -> int:
        """Return the first None index."""
        for k, v in self.parents.items():
            if k >= 0 and v == None:
                return k
        return 0

    def walk_linear(self, body, docx_obj, doc) -> DoclingDocument:
        for element in body:
            tag_name = etree.QName(element).localname
            # Check for Inline Images (blip elements)
            namespaces = {
                "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
                "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
            }
            xpath_expr = XPath(".//a:blip", namespaces=namespaces)
            drawing_blip = xpath_expr(element)

            # Check for Tables
            if element.tag.endswith("tbl"):
                try:
                    self.handle_tables(element, docx_obj, doc)
                except Exception:
                    _log.debug("could not parse a table, broken docx table")

            elif drawing_blip:
                self.handle_pictures(element, docx_obj, drawing_blip, doc)
            # Check for Text
            elif tag_name in ["p"]:
                # "tcPr", "sectPr"
                self.handle_text_elements(element, docx_obj, doc)
            else:
                _log.debug(f"Ignoring element in DOCX with tag: {tag_name}")
        return doc

    def str_to_int(self, s, default=0):
        if s is None:
            return None
        try:
            return int(s)
        except ValueError:
            return default

    def split_text_and_number(self, input_string):
        match = re.match(r"(\D+)(\d+)$|^(\d+)(\D+)", input_string)
        if match:
            parts = list(filter(None, match.groups()))
            return parts
        else:
            return [input_string]

    def get_numId_and_ilvl(self, paragraph):
        # Access the XML element of the paragraph
        numPr = paragraph._element.find(
            ".//w:numPr", namespaces=paragraph._element.nsmap
        )

        if numPr is not None:
            # Get the numId element and extract the value
            numId_elem = numPr.find("w:numId", namespaces=paragraph._element.nsmap)
            ilvl_elem = numPr.find("w:ilvl", namespaces=paragraph._element.nsmap)
            numId = numId_elem.get(self.XML_KEY) if numId_elem is not None else None
            ilvl = ilvl_elem.get(self.XML_KEY) if ilvl_elem is not None else None

            return self.str_to_int(numId, default=None), self.str_to_int(
                ilvl, default=None
            )

        return None, None  # If the paragraph is not part of a list

    def get_label_and_level(self, paragraph):
        if paragraph.style is None:
            return "Normal", None
        label = paragraph.style.style_id
        if label is None:
            return "Normal", None
        if ":" in label:
            parts = label.split(":")

            if len(parts) == 2:
                return parts[0], int(parts[1])

        parts = self.split_text_and_number(label)

        if "Heading" in label and len(parts) == 2:
            parts.sort()
            label_str = ""
            label_level = 0
            if parts[0] == "Heading":
                label_str = parts[0]
                label_level = self.str_to_int(parts[1], default=None)
            if parts[1] == "Heading":
                label_str = parts[1]
                label_level = self.str_to_int(parts[0], default=None)
            return label_str, label_level
        else:
            return label, None

    def handle_text_elements(self, element, docx_obj, doc):
        paragraph = docx.text.paragraph.Paragraph(element, docx_obj)

        if paragraph.text is None:
            return
        text = paragraph.text.strip()

        # Common styles for bullet and numbered lists.
        # "List Bullet", "List Number", "List Paragraph"
        # Identify wether list is a numbered list or not
        # is_numbered = "List Bullet" not in paragraph.style.name
        is_numbered = False
        p_style_id, p_level = self.get_label_and_level(paragraph)
        numid, ilevel = self.get_numId_and_ilvl(paragraph)

        if numid == 0:
            numid = None

        # Handle lists
        if numid is not None and ilevel is not None:
            self.add_listitem(
                element,
                docx_obj,
                doc,
                p_style_id,
                p_level,
                numid,
                ilevel,
                text,
                is_numbered,
            )
            self.update_history(p_style_id, p_level, numid, ilevel)
            return
        elif numid is None and self.prev_numid() is not None:  # Close list
            for key, val in self.parents.items():
                if key >= self.level_at_new_list:
                    self.parents[key] = None
            self.level = self.level_at_new_list - 1
            self.level_at_new_list = None
        if p_style_id in ["Title"]:
            for key, val in self.parents.items():
                self.parents[key] = None
            self.parents[0] = doc.add_text(
                parent=None, label=DocItemLabel.TITLE, text=text
            )
        elif "Heading" in p_style_id:
            self.add_header(element, docx_obj, doc, p_style_id, p_level, text)

        elif p_style_id in [
            "Paragraph",
            "Normal",
            "Subtitle",
            "Author",
            "DefaultText",
            "ListParagraph",
            "ListBullet",
            "Quote",
        ]:
            level = self.get_level()
            doc.add_text(
                label=DocItemLabel.PARAGRAPH, parent=self.parents[level - 1], text=text
            )

        else:
            # Text style names can, and will have, not only default values but user values too
            # hence we treat all other labels as pure text
            level = self.get_level()
            doc.add_text(
                label=DocItemLabel.PARAGRAPH, parent=self.parents[level - 1], text=text
            )

        self.update_history(p_style_id, p_level, numid, ilevel)
        return

    def add_header(self, element, docx_obj, doc, curr_name, curr_level, text: str):
        level = self.get_level()
        if isinstance(curr_level, int):
            if curr_level > level:
                # add invisible group
                for i in range(level, curr_level):
                    self.parents[i] = doc.add_group(
                        parent=self.parents[i - 1],
                        label=GroupLabel.SECTION,
                        name=f"header-{i}",
                    )
            elif curr_level < level:
                # remove the tail
                for key, val in self.parents.items():
                    if key >= curr_level:
                        self.parents[key] = None

            self.parents[curr_level] = doc.add_heading(
                parent=self.parents[curr_level - 1],
                text=text,
                level=curr_level,
            )
        else:
            self.parents[self.level] = doc.add_heading(
                parent=self.parents[self.level - 1],
                text=text,
                level=1,
            )
        return

    def add_listitem(
        self,
        element,
        docx_obj,
        doc,
        p_style_id,
        p_level,
        numid,
        ilevel,
        text: str,
        is_numbered=False,
    ):
        # is_numbered = is_numbered
        enum_marker = ""

        level = self.get_level()
        if self.prev_numid() is None:  # Open new list
            self.level_at_new_list = level  # type: ignore

            self.parents[level] = doc.add_group(
                label=GroupLabel.LIST, name="list", parent=self.parents[level - 1]
            )

            # Set marker and enumerated arguments if this is an enumeration element.
            self.listIter += 1
            if is_numbered:
                enum_marker = str(self.listIter) + "."
                is_numbered = True
            doc.add_list_item(
                marker=enum_marker,
                enumerated=is_numbered,
                parent=self.parents[level],
                text=text,
            )

        elif (
            self.prev_numid() == numid and self.prev_indent() < ilevel
        ):  # Open indented list
            for i in range(
                self.level_at_new_list + self.prev_indent() + 1,
                self.level_at_new_list + ilevel + 1,
            ):
                # Determine if this is an unordered list or an ordered list.
                # Set GroupLabel.ORDERED_LIST when it fits.
                self.listIter = 0
                if is_numbered:
                    self.parents[i] = doc.add_group(
                        label=GroupLabel.ORDERED_LIST,
                        name="list",
                        parent=self.parents[i - 1],
                    )
                else:
                    self.parents[i] = doc.add_group(
                        label=GroupLabel.LIST, name="list", parent=self.parents[i - 1]
                    )

            # TODO: Set marker and enumerated arguments if this is an enumeration element.
            self.listIter += 1
            if is_numbered:
                enum_marker = str(self.listIter) + "."
                is_numbered = True
            doc.add_list_item(
                marker=enum_marker,
                enumerated=is_numbered,
                parent=self.parents[self.level_at_new_list + ilevel],
                text=text,
            )

        elif self.prev_numid() == numid and ilevel < self.prev_indent():  # Close list
            for k, v in self.parents.items():
                if k > self.level_at_new_list + ilevel:
                    self.parents[k] = None

            # TODO: Set marker and enumerated arguments if this is an enumeration element.
            self.listIter += 1
            if is_numbered:
                enum_marker = str(self.listIter) + "."
                is_numbered = True
            doc.add_list_item(
                marker=enum_marker,
                enumerated=is_numbered,
                parent=self.parents[self.level_at_new_list + ilevel],
                text=text,
            )
            self.listIter = 0

        elif self.prev_numid() == numid or self.prev_indent() == ilevel:
            # TODO: Set marker and enumerated arguments if this is an enumeration element.
            self.listIter += 1
            if is_numbered:
                enum_marker = str(self.listIter) + "."
                is_numbered = True
            doc.add_list_item(
                marker=enum_marker,
                enumerated=is_numbered,
                parent=self.parents[level - 1],
                text=text,
            )
        return

    def handle_tables(self, element, docx_obj, doc):

        # Function to check if a cell has a colspan (gridSpan)
        def get_colspan(cell):
            grid_span = cell._element.xpath("@w:gridSpan")
            if grid_span:
                return int(grid_span[0])  # Return the number of columns spanned
            return 1  # Default is 1 (no colspan)

        # Function to check if a cell has a rowspan (vMerge)
        def get_rowspan(cell):
            v_merge = cell._element.xpath("@w:vMerge")
            if v_merge:
                return v_merge[
                    0
                ]  # 'restart' indicates the beginning of a rowspan, others are continuation
            return 1

        table = docx.table.Table(element, docx_obj)

        num_rows = len(table.rows)
        num_cols = 0
        for row in table.rows:
            # Calculate the max number of columns
            num_cols = max(num_cols, sum(get_colspan(cell) for cell in row.cells))

        if num_rows == 1 and num_cols == 1:
            cell_element = table.rows[0].cells[0]
            # In case we have a table of only 1 cell, we consider it furniture
            # And proceed processing the content of the cell as though it's in the document body
            self.walk_linear(cell_element._element, docx_obj, doc)
            return

        # Initialize the table grid
        table_grid = [[None for _ in range(num_cols)] for _ in range(num_rows)]

        data = TableData(num_rows=num_rows, num_cols=num_cols, table_cells=[])

        for row_idx, row in enumerate(table.rows):
            col_idx = 0
            for c, cell in enumerate(row.cells):
                row_span = get_rowspan(cell)
                col_span = get_colspan(cell)

                cell_text = cell.text
                # In case cell doesn't return text via docx library:
                if len(cell_text) == 0:
                    cell_xml = cell._element

                    texts = [""]
                    for elem in cell_xml.iter():
                        if elem.tag.endswith("t"):  # <w:t> tags that contain text
                            if elem.text:
                                texts.append(elem.text)
                    # Join the collected text
                    cell_text = " ".join(texts).strip()

                # Find the next available column in the grid
                while table_grid[row_idx][col_idx] is not None:
                    col_idx += 1

                # Fill the grid with the cell value, considering rowspan and colspan
                for i in range(row_span if row_span == "restart" else 1):
                    for j in range(col_span):
                        table_grid[row_idx + i][col_idx + j] = ""

                cell = TableCell(
                    text=cell_text,
                    row_span=row_span,
                    col_span=col_span,
                    start_row_offset_idx=row_idx,
                    end_row_offset_idx=row_idx + row_span,
                    start_col_offset_idx=col_idx,
                    end_col_offset_idx=col_idx + col_span,
                    col_header=False,
                    row_header=False,
                )

                data.table_cells.append(cell)

        level = self.get_level()
        doc.add_table(data=data, parent=self.parents[level - 1])
        return

    def handle_pictures(self, element, docx_obj, drawing_blip, doc):
        def get_docx_image(element, drawing_blip):
            rId = drawing_blip[0].get(
                "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
            )
            if rId in docx_obj.part.rels:
                # Access the image part using the relationship ID
                image_part = docx_obj.part.rels[rId].target_part
                image_data = image_part.blob  # Get the binary image data
            return image_data

        image_data = get_docx_image(element, drawing_blip)
        image_bytes = BytesIO(image_data)
        level = self.get_level()
        # Open the BytesIO object with PIL to create an Image
        try:
            pil_image = Image.open(image_bytes)
            doc.add_picture(
                parent=self.parents[level - 1],
                image=ImageRef.from_pil(image=pil_image, dpi=72),
                caption=None,
            )
        except (UnidentifiedImageError, OSError) as e:
            _log.warning("Warning: image cannot be loaded by Pillow")
            doc.add_picture(
                parent=self.parents[level - 1],
                caption=None,
            )
        return
