import logging
from io import BytesIO
from pathlib import Path
from typing import Set, Union
import pubmed_parser  # type: ignore
from bs4 import BeautifulSoup

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
from docling.datamodel.document import InputDocument

_log = logging.getLogger(__name__)


class PubMedDocumentBackend(DeclarativeDocumentBackend):
    def __init__(self, in_doc: "InputDocument", path_or_stream: Union[BytesIO, Path]):
        super().__init__(in_doc, path_or_stream)
        self.path_or_stream = path_or_stream

        # Initialize parents for the document hierarchy
        self.parents: dict = {}

    def is_valid(self) -> bool:
        return True

    @classmethod
    def supports_pagination(cls) -> bool:
        return False

    def unload(self):
        if isinstance(self.path_or_stream, BytesIO):
            self.path_or_stream.close()
        self.path_or_stream = None

    @classmethod
    def supported_formats(cls) -> Set[InputFormat]:
        return {InputFormat.PUBMED}

    def convert(self) -> DoclingDocument:
        # Create empty document
        origin = DocumentOrigin(
            filename=self.file.name or "file",
            mimetype="text/xml",
            binary_hash=self.document_hash,
        )
        doc = DoclingDocument(name=self.file.stem or "file", origin=origin)

        _log.debug("Trying to convert XML...")

        # Get parsed XML components
        xml_components: dict = self.parse(str(self.file))

        # Add XML components to the document
        doc = self.populate_document(doc, xml_components)
        return doc

    def parse(self, filename: str) -> dict:
        """Parsing PubMed document."""
        try:
            info = pubmed_parser.parse_pubmed_xml(filename, include_path=True)
        except Exception as e:
            print(f"Skipping title, authors and abstract for: {filename}")
            info = None
        references: list = pubmed_parser.parse_pubmed_references(filename)
        figure_captions: list = pubmed_parser.parse_pubmed_caption(filename)
        paragraphs: list = pubmed_parser.parse_pubmed_paragraph(filename)
        tables: list = pubmed_parser.parse_pubmed_table(filename, return_xml=True)

        return {
            "info": info,
            "references": references,
            "figure_captions": figure_captions,
            "paragraphs": paragraphs,
            "tables": tables,
        }

    def populate_document(
        self, doc: DoclingDocument, xml_components: dict
    ) -> DoclingDocument:
        if xml_components["info"] != None:
            self.add_title(doc, xml_components)
            self.add_authors(doc, xml_components)
            self.add_abstract(doc, xml_components)

        self.add_main_text(doc, xml_components)

        if xml_components["tables"] != None:
            self.add_tables(doc, xml_components)

        if xml_components["figure_captions"] != None:
            self.add_figure_captions(doc, xml_components)

        self.add_references(doc, xml_components)

        return doc

    def add_figure_captions(self, doc: DoclingDocument, xml_components: dict) -> None:
        doc.add_heading(parent=self.parents["Title"], text="Figures")
        for figure_caption_xml_component in xml_components["figure_captions"]:
            figure_caption_text = (
                figure_caption_xml_component["fig_label"]
                + " "
                + figure_caption_xml_component["fig_caption"].replace("\n", "")
            )
            fig_caption = doc.add_text(
                label=DocItemLabel.CAPTION, text=figure_caption_text
            )
            doc.add_picture(
                parent=self.parents["Title"],
                caption=fig_caption,
            )
        return

    def add_title(self, doc: DoclingDocument, xml_components: dict) -> None:
        self.parents["Title"] = doc.add_text(
            parent=None,
            text=xml_components["info"]["full_title"],
            label=DocItemLabel.TITLE,
        )        
        return

    def add_authors(self, doc: DoclingDocument, xml_components: dict) -> None:
        affiliations_map: dict = {}
        for affiliation in xml_components["info"]["affiliation_list"]:
            affiliations_map[affiliation[0]] = affiliation[1]

        authors: dict = {}
        for authorlist in xml_components["info"]["author_list"]:
            authorlist_ = reversed([name for name in authorlist[:-1] if name])
            author = " ".join(authorlist_)
            if not author.strip():
                continue
            if author not in authors.keys():
                authors[author] = []
            aff_index = authorlist[-1]
            affiliation = affiliations_map[aff_index]
            authors[author].append({"name": affiliation})

        authors_affiliations: list = []
        for author, affiliations_ in authors.items():
            authors_affiliations.append(author)
            for affiliation in affiliations_:
                authors_affiliations.append(affiliation["name"])

        doc.add_text(
            parent=self.parents["Title"],
            text="; ".join(authors_affiliations),
            label=DocItemLabel.PARAGRAPH,
        )
        return

    def add_abstract(self, doc: DoclingDocument, xml_components: dict) -> None:
        abstract_text: str = (
            xml_components["info"]["abstract"].replace("\n", " ").strip()
        )
        if abstract_text.strip():
            self.parents["Abstract"] = doc.add_heading(parent=self.parents["Title"], text="Abstract")
            doc.add_text(
                parent=self.parents["Abstract"],
                text=abstract_text, 
                label=DocItemLabel.TEXT
            )
        return

    def add_main_text(self, doc: DoclingDocument, xml_components: dict) -> None:
        sections: list = []
        for paragraph in xml_components["paragraphs"]:
            if ("section" in paragraph) and (paragraph["section"] == ""):
                continue

            if "section" in paragraph and paragraph["section"] not in sections:
                section: str = paragraph["section"].replace("\n", " ").strip()
                sections.append(section)
                if section in self.parents:
                    parent = self.parents[section]
                else:
                    parent = self.parents["Title"]

                self.parents[section] = doc.add_heading(parent=parent, text=section)

            if "text" in paragraph:
                text: str = paragraph["text"].replace("\n", " ").strip()

                if paragraph["section"] in self.parents:
                    parent = self.parents[paragraph["section"]]
                else:
                    parent = self.parents["Title"]

                doc.add_text(parent=parent, label=DocItemLabel.TEXT, text=text)
        return

    def add_references(self, doc: DoclingDocument, xml_components: dict) -> None:
        self.parents["References"] = doc.add_heading(parent=self.parents["Title"], text="References")
        current_list = doc.add_group(
            parent=self.parents["References"], 
            label=GroupLabel.LIST, 
            name="list"
        )
        for reference in xml_components["references"]:
            reference_text: str = ""            
            if reference["name"] != "":
                reference_text += reference["name"] + ". "

            if reference["article_title"] != "":
                reference_text += reference["article_title"] 
                if reference["article_title"][-1] != ".":
                    reference_text += "."
                reference_text += " "

            if reference["journal"] != "":
                reference_text += reference["journal"]  

            if reference["year"] != "":
                reference_text += " (" + reference["year"] + ")"

            if reference_text == "":
                print(f"Skipping reference for: {str(self.file)}")
                continue

            doc.add_list_item(
                text=reference_text, enumerated=False, parent=current_list
            )
        return

    def add_tables(self, doc: DoclingDocument, xml_components: dict) -> None:
        self.parents["Tables"] = doc.add_heading(parent=self.parents["Title"], text="Tables")
        for table_xml_component in xml_components["tables"]:
            try:
                self.add_table(doc, table_xml_component)
            except Exception as e:
                print(f"Skipping unsupported table for: {str(self.file)}")
                pass
        return

    def add_table(self, doc: DoclingDocument, table_xml_component: dict) -> None:
        table_xml = table_xml_component["table_xml"].decode("utf-8")
        soup = BeautifulSoup(table_xml, "html.parser")
        table_tag = soup.find("table")

        nested_tables = table_tag.find("table")
        if nested_tables is not None:
            print(f"Skipping nested table for: {str(self.file)}")
            return

        # Count the number of rows (number of <tr> elements)
        num_rows = len(table_tag.find_all("tr"))

        # Find the number of columns (taking into account colspan)
        num_cols = 0
        for row in table_tag.find_all("tr"):
            col_count = 0
            for cell in row.find_all(["td", "th"]):
                colspan = int(cell.get("colspan", 1))
                col_count += colspan
            num_cols = max(num_cols, col_count)

        grid = [[None for _ in range(num_cols)] for _ in range(num_rows)]

        data = TableData(num_rows=num_rows, num_cols=num_cols, table_cells=[])

        # Iterate over the rows in the table
        for row_idx, row in enumerate(table_tag.find_all("tr")):

            # For each row, find all the column cells (both <td> and <th>)
            cells = row.find_all(["td", "th"])

            # Check if each cell in the row is a header -> means it is a column header
            col_header = True
            for j, html_cell in enumerate(cells):
                if html_cell.name == "td":
                    col_header = False

            col_idx = 0
            # Extract and print the text content of each cell
            for _, html_cell in enumerate(cells):
                text = html_cell.text

                col_span = int(html_cell.get("colspan", 1))
                row_span = int(html_cell.get("rowspan", 1))

                while grid[row_idx][col_idx] is not None:
                    col_idx += 1
                for r in range(row_span):
                    for c in range(col_span):
                        grid[row_idx + r][col_idx + c] = text

                cell = TableCell(
                    text=text,
                    row_span=row_span,
                    col_span=col_span,
                    start_row_offset_idx=row_idx,
                    end_row_offset_idx=row_idx + row_span,
                    start_col_offset_idx=col_idx,
                    end_col_offset_idx=col_idx + col_span,
                    col_header=col_header,
                    row_header=((not col_header) and html_cell.name == "th"),
                )
                data.table_cells.append(cell)

        table_caption = doc.add_text(
            label=DocItemLabel.CAPTION,
            text=table_xml_component["label"] + " " + table_xml_component["caption"],
        )
        doc.add_table(
            data=data, 
            parent=self.parents["Tables"], 
            caption=table_caption
        )
        return
