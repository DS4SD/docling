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
import marko.ext
import marko.ext.gfm
import marko.inline

from docling.backend.abstract_backend import (
    DeclarativeDocumentBackend
)
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import InputDocument

import marko
from marko import Markdown
# from marko.ext.gfm import gfm  # GitHub Flavored Markdown plugin (tables, task lists, etc.)
# from marko.ext.gfm.elements import Table
# from marko.ext.gfm.elements import TableCell
# from marko.ext.gfm.elements import TableRow

# from marko.block import BlockElement
# from marko.inline import InlineElement

_log = logging.getLogger(__name__)


class MarkdownDocumentBackend(DeclarativeDocumentBackend):
    def __init__(self, in_doc: "InputDocument", path_or_stream: Union[BytesIO, Path]):
        super().__init__(in_doc, path_or_stream)

        _log.info("MD INIT!!!")

        # Markdown file:
        self.path_or_stream = path_or_stream
        self.valid = True
        self.markdown = ""  # To store original Markdown string

        self.in_table = False
        self.md_table_buffer = []

        try:
            if isinstance(self.path_or_stream, BytesIO):
                text_stream = self.path_or_stream.getvalue().decode("utf-8")
                self.markdown = text_stream
            if isinstance(self.path_or_stream, Path):
                with open(self.path_or_stream, "r", encoding="utf-8") as f:
                    md_content = f.read()
                    self.markdown = md_content
            self.valid = True

            _log.info(self.markdown)
        except Exception as e:
            raise RuntimeError(
                f"Could not initialize MD backend for file with hash {self.document_hash}."
            ) from e
        return

    def close_table(self):
        if self.in_table:
            print("")
            print("====================================== TABLE START")
            for md_table_row in self.md_table_buffer:
                print(md_table_row)
            print("====================================== TABLE END")
            print("")
            self.in_table = False
            self.md_table_buffer = []  # clean table markdown buffer
        # return self.in_table, self.md_table_buffer
        return

    # Function to iterate over all elements in the AST
    def iterate_elements(self, element, depth=0, doc=None, parent_element = None):
        # Print the element type and optionally its content
        # print(f"{'  ' * depth}- {type(element).__name__}", end="")
        # print(f"{'  ' * depth}", end="")
        
        # if isinstance(element, BlockElement):
        #     print(" (Block Element)")
        # elif isinstance(element, InlineElement):
        #     print(" (Inline Element)")

        # not_a_list_item = True


        # Check for different element types and print relevant details
        if isinstance(element, marko.block.Heading):
            self.close_table()
            # print(f" - Heading level {element.level}, content: {element.children[0].children}")
            if element.level == 1:
                doc_label = DocItemLabel.TITLE
            else:
                doc_label = DocItemLabel.SECTION_HEADER
            snippet_text = element.children[0].children

            parent_element = doc.add_text(
                label=doc_label,
                parent=parent_element,
                text=snippet_text
            )

        
        elif isinstance(element, marko.block.List):
            self.close_table()
            # print(f" - List {'ordered' if element.ordered else 'unordered'}")
            list_label = GroupLabel.LIST
            if element.ordered:
                list_label = GroupLabel.ORDERED_LIST
            parent_element = doc.add_group(
                label=list_label,
                name=f"list",
                parent=parent_element
            )
        
        elif isinstance(element, marko.block.ListItem):
            self.close_table()
            # print(" - List item")
            # not_a_list_item = False
            snippet_text = str(element.children[0].children[0].children)
            is_numbered = False
            if parent_element.label == GroupLabel.ORDERED_LIST:
                is_numbered = True
            doc.add_list_item(
                # marker=enum_marker,
                enumerated=is_numbered,
                parent=parent_element,
                text=snippet_text
            )

        elif isinstance(element, marko.block.Paragraph):
            self.close_table()
            # print(f" - Paragraph: {element.children[0].children}")
            snippet_text = str(element.children[0].children)
            doc.add_text(
                label=DocItemLabel.PARAGRAPH,
                parent=parent_element,
                text=snippet_text
            )
        
        elif isinstance(element, marko.inline.Image):
            self.close_table()
            # print(f" - Image with alt: {element.title}, url: {element.dest}")
            doc.add_picture(
                parent=parent_element,
                caption=element.title
            )

        elif isinstance(element, marko.inline.RawText):
            # print(f" - Paragraph (raw text): {element.children}")
            # TODO: Detect start of the table here...
            snippet_text = str(element.children)
            if "|" in snippet_text:
                # most likely table
                # if in_table == False:
                #     print("====================================== TABLE START!")
                self.in_table = True
                # print(f" - TABLE: {element.children}")
                if len(self.md_table_buffer) > 0:
                    self.md_table_buffer[len(self.md_table_buffer)-1] += str(snippet_text)
                else:
                    self.md_table_buffer.append(snippet_text)
            else:
                self.close_table()
                self.in_table = False
                # most likely just text
                doc.add_text(
                    label=DocItemLabel.PARAGRAPH,
                    parent=parent_element,
                    text=snippet_text
                )

        elif isinstance(element, marko.inline.CodeSpan):
            self.close_table()
            # print(f" - Paragraph (code): {element.children}")
            snippet_text = str(element.children)
            doc.add_text(
                label=DocItemLabel.CODE,
                parent=parent_element,
                text=snippet_text
            )

        elif isinstance(element, marko.inline.LineBreak):
            if self.in_table:
                print("Line break in table")
                self.md_table_buffer.append("")
                # print("HTML Block else: {}".format(element))

        elif isinstance(element, marko.block.HTMLBlock):
            self.close_table()
            print("HTML Block else: {}".format(element))

            # elif isinstance(element, marko.ext.gfm.elements.Table):
        # elif isinstance(element, marko.ext.gfm.elements.Table):
        #     print(" - Table")
        # elif isinstance(element, TableRow):
        #     print(" - TableRow")
        # elif isinstance(element, TableCell):
        #     print(" - TableCell")
        else:
            if not isinstance(element, str):
                self.close_table()
                print("Something else: {}".format(element))

        # elif isinstance(element, marko.block.Table):
        #     print(" - Table")

        # Iterate through the element's children (if any)
        if hasattr(element, 'children'):
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
        return False  # True? if so, how to handle pages...

    @classmethod
    def supported_formats(cls) -> Set[InputFormat]:
        return {InputFormat.MD}

    def convert(self) -> DoclingDocument:
        print("converting Markdown...")
        doc = DoclingDocument(name="Test")
        # doc.add_text(label=DocItemLabel.PARAGRAPH, text="Markdown conversion")

        if self.is_valid():
            # Parse the markdown into an abstract syntax tree (AST)
            # parser = marko.Markdown(extensions=['gfm'])

            # gfm_parser = Markdown(extensions=['gfm'])
            gfm_parser = Markdown()
            # gfm_parser.use('gfm')
            
            parsed_ast = gfm_parser.parse(self.markdown)

            # parsed_ast = gfm(self.markdown)
            # Start iterating from the root of the AST
            self.iterate_elements(parsed_ast, 0 , doc, None)

        else:
            raise RuntimeError(
                f"Cannot convert md with {self.document_hash} because the backend failed to init."
            )
        return doc