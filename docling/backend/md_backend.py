import logging
from io import BytesIO
from pathlib import Path
from typing import Set, Union

from docling_core.types.doc import (
    BoundingBox,
    CoordOrigin,
    DocItemLabel,
    DoclingDocument,
    DocumentOrigin,
    GroupLabel,
    ProvenanceItem,
    Size,
    TableCell,
    TableData,
)

from docling.backend.abstract_backend import (
    DeclarativeDocumentBackend,
    PaginatedDocumentBackend,
)
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import InputDocument

import marko
from marko.block import Heading, List, ListItem, Paragraph, BlockQuote, FencedCode, Table, TableRow, TableCell
from marko.inline import Image, Link, Emphasis, Strong

_log = logging.getLogger(__name__)


class MarkdownToDoclingRenderer(marko.Renderer):
    """
    # This is text analog of object based methods...
    def render_heading(self, element: Heading):
        return f"{'#' * element.level} {self.render_children(element)}\n\n"

    def render_list(self, element: List):
        if element.ordered:
            return ''.join(f"{i+1}. {self.render(child)}\n" for i, child in enumerate(element.children))
        else:
            return ''.join(f"* {self.render(child)}\n" for child in element.children)

    def render_list_item(self, element: ListItem):
        return self.render_children(element)

    def render_paragraph(self, element: Paragraph):
        return f"{self.render_children(element)}\n\n"

    def render_image(self, element: Image):
        return f"![{element.title}]({element.dest})\n\n"

    def render_table(self, element: Table):
        rows = [self.render(child) for child in element.children]
        return '\n'.join(rows) + '\n'

    def render_table_row(self, element: TableRow):
        cells = ' | '.join(self.render(cell) for cell in element.children)
        return f"| {cells} |"

    def render_table_cell(self, element: TableCell):
        return self.render_children(element)
    """
    def render_heading(self, element: Heading):
        return {
            "type": "heading",
            "level": element.level,
            "content": self.render_children(element),
        }

    def render_paragraph(self, element: Paragraph):
        return {
            "type": "paragraph",
            "content": self.render_children(element),
        }

    def render_list(self, element: List):
        return {
            "type": "list",
            "ordered": element.ordered,
            "items": [self.render(child) for child in element.children]
        }

    def render_list_item(self, element: ListItem):
        return {
            "type": "list_item",
            "content": self.render_children(element),
        }

    def render_image(self, element: Image):
        return {
            "type": "image",
            "alt": element.title,
            "url": element.dest,
        }

    def render_table(self, element: Table):
        return {
            "type": "table",
            "rows": [self.render(row) for row in element.children]
        }

    def render_table_row(self, element: TableRow):
        return {
            "type": "table_row",
            "cells": [self.render(cell) for cell in element.children]
        }

    def render_table_cell(self, element: TableCell):
        return {
            "type": "table_cell",
            "content": self.render_children(element)
        }

    def render(self, element):
        if isinstance(element, str):
            return element
        return super().render(element)

class MarkdownDocumentBackend(DeclarativeDocumentBackend, PaginatedDocumentBackend):
    def __init__(self, in_doc: "InputDocument", path_or_stream: Union[BytesIO, Path]):
        super().__init__(in_doc, path_or_stream)
        # Markdown file:
        self.path_or_stream = path_or_stream

        self.valid = False

        try:
            if isinstance(self.path_or_stream, BytesIO):
                text_stream = self.path_or_stream.getvalue().decode("utf-8")
                self.markdown = text_stream
            if isinstance(self.path_or_stream, Path):
                with open(self.path_or_stream, "r", encoding="utf-8") as f:
                    md_content = f.read()
                    self.markdown = md_content
        except Exception as e:
            raise RuntimeError(
                f"Could not initialize MD backend for file with hash {self.document_hash}."
            ) from e
        return

    def page_count(self) -> int:
        return 0

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
        return {InputFormat.MD}

    def convert(self) -> DoclingDocument:
            # Parse and render
            parser = marko.Markdown(renderer=MarkdownToDoclingRenderer)
            parsed_object = parser.parse(markdown_text)
            # Render the parsed Markdown into a structured object
            markdown_object = parser.render(parsed_object)

            print(marko_doc)
            # doc = self.walk(self.soup.body, doc)
        else:
            raise RuntimeError(
                f"Cannot convert md with {self.document_hash} because the backend failed to init."
            )
        return doc