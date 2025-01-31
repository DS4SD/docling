import logging
import re
import warnings
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Set, Union

import marko
import marko.element
import marko.ext
import marko.ext.gfm
import marko.inline
from docling_core.types.doc import (
    DocItem,
    DocItemLabel,
    DoclingDocument,
    DocumentOrigin,
    GroupLabel,
    NodeItem,
    TableCell,
    TableData,
    TextItem,
)
from marko import Markdown

from docling.backend.abstract_backend import DeclarativeDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import InputDocument

_log = logging.getLogger(__name__)


class MarkdownDocumentBackend(DeclarativeDocumentBackend):
    def shorten_underscore_sequences(self, markdown_text: str, max_length: int = 10):
        # This regex will match any sequence of underscores
        pattern = r"_+"

        def replace_match(match):
            underscore_sequence = match.group(
                0
            )  # Get the full match (sequence of underscores)

            # Shorten the sequence if it exceeds max_length
            if len(underscore_sequence) > max_length:
                return "_" * max_length
            else:
                return underscore_sequence  # Leave it unchanged if it is shorter or equal to max_length

        # Use re.sub to replace long underscore sequences
        shortened_text = re.sub(pattern, replace_match, markdown_text)

        if len(shortened_text) != len(markdown_text):
            warnings.warn("Detected potentially incorrect Markdown, correcting...")

        return shortened_text

    def __init__(self, in_doc: "InputDocument", path_or_stream: Union[BytesIO, Path]):
        super().__init__(in_doc, path_or_stream)

        _log.debug("MD INIT!!!")

        # Markdown file:
        self.path_or_stream = path_or_stream
        self.valid = True
        self.markdown = ""  # To store original Markdown string

        self.in_table = False
        self.md_table_buffer: list[str] = []
        self.inline_texts: list[str] = []

        try:
            if isinstance(self.path_or_stream, BytesIO):
                text_stream = self.path_or_stream.getvalue().decode("utf-8")
                # remove invalid sequences
                # very long sequences of underscores will lead to unnecessary long processing times.
                # In any proper Markdown files, underscores have to be escaped,
                # otherwise they represent emphasis (bold or italic)
                self.markdown = self.shorten_underscore_sequences(text_stream)
            if isinstance(self.path_or_stream, Path):
                with open(self.path_or_stream, "r", encoding="utf-8") as f:
                    md_content = f.read()
                    # remove invalid sequences
                    # very long sequences of underscores will lead to unnecessary long processing times.
                    # In any proper Markdown files, underscores have to be escaped,
                    # otherwise they represent emphasis (bold or italic)
                    self.markdown = self.shorten_underscore_sequences(md_content)
            self.valid = True

            _log.debug(self.markdown)
        except Exception as e:
            raise RuntimeError(
                f"Could not initialize MD backend for file with hash {self.document_hash}."
            ) from e
        return

    def close_table(self, doc: DoclingDocument):
        if self.in_table:
            _log.debug("=== TABLE START ===")
            for md_table_row in self.md_table_buffer:
                _log.debug(md_table_row)
            _log.debug("=== TABLE END ===")
            tcells: List[TableCell] = []
            result_table = []
            for n, md_table_row in enumerate(self.md_table_buffer):
                data = []
                if n == 0:
                    header = [t.strip() for t in md_table_row.split("|")[1:-1]]
                    for value in header:
                        data.append(value)
                    result_table.append(data)
                if n > 1:
                    values = [t.strip() for t in md_table_row.split("|")[1:-1]]
                    for value in values:
                        data.append(value)
                    result_table.append(data)

            for trow_ind, trow in enumerate(result_table):
                for tcol_ind, cellval in enumerate(trow):
                    row_span = (
                        1  # currently supporting just simple tables (without spans)
                    )
                    col_span = (
                        1  # currently supporting just simple tables (without spans)
                    )
                    icell = TableCell(
                        text=cellval.strip(),
                        row_span=row_span,
                        col_span=col_span,
                        start_row_offset_idx=trow_ind,
                        end_row_offset_idx=trow_ind + row_span,
                        start_col_offset_idx=tcol_ind,
                        end_col_offset_idx=tcol_ind + col_span,
                        col_header=False,
                        row_header=False,
                    )
                    tcells.append(icell)

            num_rows = len(result_table)
            num_cols = len(result_table[0])
            self.in_table = False
            self.md_table_buffer = []  # clean table markdown buffer
            # Initialize Docling TableData
            table_data = TableData(
                num_rows=num_rows, num_cols=num_cols, table_cells=tcells
            )
            # Populate
            for tcell in tcells:
                table_data.table_cells.append(tcell)
            if len(tcells) > 0:
                doc.add_table(data=table_data)
        return

    def process_inline_text(
        self, parent_element: Optional[NodeItem], doc: DoclingDocument
    ):
        txt = " ".join(self.inline_texts)
        if len(txt) > 0:
            doc.add_text(
                label=DocItemLabel.PARAGRAPH,
                parent=parent_element,
                text=txt,
            )
        self.inline_texts = []

    def iterate_elements(
        self,
        element: marko.element.Element,
        depth: int,
        doc: DoclingDocument,
        parent_element: Optional[NodeItem] = None,
    ):
        # Iterates over all elements in the AST
        # Check for different element types and process relevant details
        if isinstance(element, marko.block.Heading) and len(element.children) > 0:
            self.close_table(doc)
            self.process_inline_text(parent_element, doc)
            _log.debug(
                f" - Heading level {element.level}, content: {element.children[0].children}"  # type: ignore
            )
            if element.level == 1:
                doc_label = DocItemLabel.TITLE
            else:
                doc_label = DocItemLabel.SECTION_HEADER

            # Header could have arbitrary inclusion of bold, italic or emphasis,
            # hence we need to traverse the tree to get full text of a header
            strings: List[str] = []

            # Define a recursive function to traverse the tree
            def traverse(node: marko.block.BlockElement):
                # Check if the node has a "children" attribute
                if hasattr(node, "children"):
                    # If "children" is a list, continue traversal
                    if isinstance(node.children, list):
                        for child in node.children:
                            traverse(child)
                    # If "children" is text, add it to header text
                    elif isinstance(node.children, str):
                        strings.append(node.children)

            traverse(element)
            snippet_text = "".join(strings)
            if len(snippet_text) > 0:
                parent_element = doc.add_text(
                    label=doc_label, parent=parent_element, text=snippet_text
                )

        elif isinstance(element, marko.block.List):
            has_non_empty_list_items = False
            for child in element.children:
                if isinstance(child, marko.block.ListItem) and len(child.children) > 0:
                    has_non_empty_list_items = True
                    break

            self.close_table(doc)
            self.process_inline_text(parent_element, doc)
            _log.debug(f" - List {'ordered' if element.ordered else 'unordered'}")
            if has_non_empty_list_items:
                label = GroupLabel.ORDERED_LIST if element.ordered else GroupLabel.LIST
                parent_element = doc.add_group(
                    label=label, name=f"list", parent=parent_element
                )

        elif isinstance(element, marko.block.ListItem) and len(element.children) > 0:
            self.close_table(doc)
            self.process_inline_text(parent_element, doc)
            _log.debug(" - List item")

            snippet_text = str(element.children[0].children[0].children)  # type: ignore
            is_numbered = False
            if (
                parent_element is not None
                and isinstance(parent_element, DocItem)
                and parent_element.label == GroupLabel.ORDERED_LIST
            ):
                is_numbered = True
            doc.add_list_item(
                enumerated=is_numbered, parent=parent_element, text=snippet_text
            )

        elif isinstance(element, marko.inline.Image):
            self.close_table(doc)
            self.process_inline_text(parent_element, doc)
            _log.debug(f" - Image with alt: {element.title}, url: {element.dest}")

            fig_caption: Optional[TextItem] = None
            if element.title is not None and element.title != "":
                fig_caption = doc.add_text(
                    label=DocItemLabel.CAPTION, text=element.title
                )

            doc.add_picture(parent=parent_element, caption=fig_caption)

        elif isinstance(element, marko.block.Paragraph) and len(element.children) > 0:
            self.process_inline_text(parent_element, doc)

        elif isinstance(element, marko.inline.RawText):
            _log.debug(f" - Paragraph (raw text): {element.children}")
            snippet_text = element.children.strip()
            # Detect start of the table:
            if "|" in snippet_text:
                # most likely part of the markdown table
                self.in_table = True
                if len(self.md_table_buffer) > 0:
                    self.md_table_buffer[len(self.md_table_buffer) - 1] += snippet_text
                else:
                    self.md_table_buffer.append(snippet_text)
            else:
                self.close_table(doc)
                self.in_table = False
                # most likely just inline text
                self.inline_texts.append(str(element.children))

        elif isinstance(element, marko.inline.CodeSpan):
            self.close_table(doc)
            self.process_inline_text(parent_element, doc)
            _log.debug(f" - Code Span: {element.children}")
            snippet_text = str(element.children).strip()
            doc.add_code(parent=parent_element, text=snippet_text)

        elif (
            isinstance(element, (marko.block.CodeBlock, marko.block.FencedCode))
            and len(element.children) > 0
            and isinstance((first_child := element.children[0]), marko.inline.RawText)
            and len(snippet_text := (first_child.children.strip())) > 0
        ):
            self.close_table(doc)
            self.process_inline_text(parent_element, doc)
            _log.debug(f" - Code Block: {element.children}")
            doc.add_code(parent=parent_element, text=snippet_text)

        elif isinstance(element, marko.inline.LineBreak):
            if self.in_table:
                _log.debug("Line break in a table")
                self.md_table_buffer.append("")

        elif isinstance(element, marko.block.HTMLBlock):
            self.process_inline_text(parent_element, doc)
            self.close_table(doc)
            _log.debug("HTML Block: {}".format(element))
            if (
                len(element.children) > 0
            ):  # If Marko doesn't return any content for HTML block, skip it
                snippet_text = str(element.children).strip()
                doc.add_text(
                    label=DocItemLabel.CODE, parent=parent_element, text=snippet_text
                )
        else:
            if not isinstance(element, str):
                self.close_table(doc)
                _log.debug("Some other element: {}".format(element))

        processed_block_types = (
            marko.block.ListItem,
            marko.block.Heading,
            marko.block.CodeBlock,
            marko.block.FencedCode,
            # marko.block.Paragraph,
            marko.inline.RawText,
        )

        # Iterate through the element's children (if any)
        if hasattr(element, "children") and not isinstance(
            element, processed_block_types
        ):
            for child in element.children:
                self.iterate_elements(child, depth + 1, doc, parent_element)

    def is_valid(self) -> bool:
        return self.valid

    def unload(self):
        if isinstance(self.path_or_stream, BytesIO):
            self.path_or_stream.close()
        self.path_or_stream = None

    @classmethod
    def supports_pagination(cls) -> bool:
        return False

    @classmethod
    def supported_formats(cls) -> Set[InputFormat]:
        return {InputFormat.MD}

    def convert(self) -> DoclingDocument:
        _log.debug("converting Markdown...")

        origin = DocumentOrigin(
            filename=self.file.name or "file",
            mimetype="text/markdown",
            binary_hash=self.document_hash,
        )

        doc = DoclingDocument(name=self.file.stem or "file", origin=origin)

        if self.is_valid():
            # Parse the markdown into an abstract syntax tree (AST)
            marko_parser = Markdown()
            parsed_ast = marko_parser.parse(self.markdown)
            # Start iterating from the root of the AST
            self.iterate_elements(parsed_ast, 0, doc, None)
            self.process_inline_text(None, doc)  # handle last hanging inline text
        else:
            raise RuntimeError(
                f"Cannot convert md with {self.document_hash} because the backend failed to init."
            )
        return doc
