import re
    
import logging
from io import BytesIO
from pathlib import Path
from typing import Set, Union

from docling_core.types.doc import (
    DocItemLabel,
    DoclingDocument,
    DocumentOrigin,
    GroupLabel,
    TableCell,
    TableData,
)

from docling.backend.abstract_backend import DeclarativeDocumentBackend
from docling.datamodel.base_models import InputFormat
#from docling.datamodel.document import InputDocument

_log = logging.getLogger(__name__)


class AsciidocBackend(DeclarativeDocumentBackend):

    def __init__(self, in_doc: "InputDocument", path_or_stream: Union[BytesIO, Path]):
        super().__init__(in_doc, path_or_stream)

        self.path_or_stream = path_or_stream

        self.valid = True
        
    def is_valid(self) -> bool:
        return self.valid

    @classmethod
    def supports_pagination(cls) -> bool:
        return False

    def unload(self):
        return

    @classmethod
    def supported_formats(cls) -> Set[InputFormat]:
        return {InputFormat.ASCIIDOC}

    def convert(self) -> DoclingDocument:
        """
        Parses the ASCII into a structured document model.
        """

        fname = ""
        if isinstance(self.path_or_stream, Path):
            fname = self.path_or_stream.name

        origin = DocumentOrigin(
            filename=fname,
            mimetype="text/asciidoc",
            binary_hash=self.document_hash,
        )
        if len(fname) > 0:
            docname = Path(fname).stem
        else:
            docname = "stream"            
        
        doc = DoclingDocument(name=docname, origin=origin)

        doc = self.parse_stream(doc)
        
        return doc

    def parse(self, doc: DoclingDocument):
        """
        Main function that orchestrates the parsing by yielding components:
        title, section headers, text, lists, and tables.
        """

        content=""
        with open(self.path_or_stream, "r") as fr:
            self.lines = fr.read_lines()
        
        #self.lines = file_content.splitlines()
        
        in_list = False
        in_table = False
        table_data = []
        
        for line in self.lines:
            line = line.strip()
            
            # Title
            if self.is_title(line):
                item = self.parse_title(line)
                doc.set_title(text=item["text"])

            # Section headers
            elif self.is_section_header(line):
                heading = self.parse_section_header(line)
                doc.add_heading(text=heading["text"], level=heading["level"])

            # Lists
            elif self.is_list_item(line):
                if not in_list:
                    in_list = True

                item = self.parse_list_item(line)
                doc.add_listitem(item["text"])
            
            elif in_list and not self.is_list_item(line):
                in_list = False
            
            # Tables
            elif self.is_table_line(line):
                in_table = True                
                table_data.append(self.parse_table_line(line))
                continue
            
            elif in_table and not self.is_table_line(line):
                
                grid = self.populate_table_as_grid(table_data)
                doc.add_table(data=grid)
                
                in_table = False
                table_data = []
            
            # Plain text
            elif line:
                item = self.parse_text(line)
                doc.add_text(text=item["text"])
        
        return doc

    # Title
    def is_title(self, line):
        return re.match(r"^= ", line)
    
    def parse_title(self, line):
        return {"type": "title", "text": line[2:].strip()}

    # Section headers
    def is_section_header(self, line):
        return re.match(r"^==+", line)

    def parse_section_header(self, line):
        header_level = line.count('=')  # number of '=' represents level
        return {"type": "header", "level": header_level, "text": line[header_level:].strip()}
    
    # Lists
    def is_list_item(self, line):
        return re.match(r"^(\*|-|\d+\.|\w+\.) ", line)

    def parse_list_item(self, line):
        return {"type": "list_item", "text": line}

    # Tables
    def is_table_line(self, line):
        return re.match(r"^\|.*\|", line)

    def parse_table_line(self, line):
        # Split table cells and trim extra spaces
        return [cell.strip() for cell in line.split('|') if cell.strip()]

    def populate_table_as_grid(self, table_data):
        # Adjust the table data into a grid format
        max_cols = max(len(row) for row in table_data)
        grid = []
        for row in table_data:
            # Pad rows with empty strings to match column count
            grid.append(row + [''] * (max_cols - len(row)))
        return grid
    
    # Plain text
    def parse_text(self, line):
        return {"type": "text", "text": line}
