import logging
from io import BytesIO
from pathlib import Path
from typing import Any, Set, Union

import lxml
from bs4 import BeautifulSoup
from docling_core.types.doc import (
    DocItemLabel,
    DoclingDocument,
    DocumentOrigin,
    GroupLabel,
    TableCell,
    TableData,
)
from lxml import etree
from typing_extensions import TypedDict, override

from docling.backend.abstract_backend import DeclarativeDocumentBackend
from docling.datamodel.base_models import InputFormat
from docling.datamodel.document import InputDocument

_log = logging.getLogger(__name__)


class Paragraph(TypedDict):
    text: str
    headers: list[str]


class Author(TypedDict):
    name: str
    affiliation_names: list[str]


class Table(TypedDict):
    label: str
    caption: str
    content: str


class FigureCaption(TypedDict):
    label: str
    caption: str


class Reference(TypedDict):
    author_names: str
    title: str
    journal: str
    year: str


class XMLComponents(TypedDict):
    title: str
    authors: list[Author]
    abstract: str
    paragraphs: list[Paragraph]
    tables: list[Table]
    figure_captions: list[FigureCaption]
    references: list[Reference]


class PubMedDocumentBackend(DeclarativeDocumentBackend):
    """
    The code from this document backend has been developed by modifying parts of the PubMed Parser library (version 0.5.0, released on 12.08.2024):
    Achakulvisut et al., (2020).
    Pubmed Parser: A Python Parser for PubMed Open-Access XML Subset and MEDLINE XML Dataset XML Dataset.
    Journal of Open Source Software, 5(46), 1979,
    https://doi.org/10.21105/joss.01979
    """

    @override
    def __init__(self, in_doc: "InputDocument", path_or_stream: Union[BytesIO, Path]):
        super().__init__(in_doc, path_or_stream)
        self.path_or_stream = path_or_stream

        # Initialize parents for the document hierarchy
        self.parents: dict = {}

        self.valid = False
        try:
            if isinstance(self.path_or_stream, BytesIO):
                self.path_or_stream.seek(0)
            self.tree: lxml.etree._ElementTree = etree.parse(self.path_or_stream)
            if "/NLM//DTD JATS" in self.tree.docinfo.public_id:
                self.valid = True
        except Exception as exc:
            raise RuntimeError(
                f"Could not initialize PubMed backend for file with hash {self.document_hash}."
            ) from exc

    @override
    def is_valid(self) -> bool:
        return self.valid

    @classmethod
    @override
    def supports_pagination(cls) -> bool:
        return False

    @override
    def unload(self):
        if isinstance(self.path_or_stream, BytesIO):
            self.path_or_stream.close()
        self.path_or_stream = None

    @classmethod
    @override
    def supported_formats(cls) -> Set[InputFormat]:
        return {InputFormat.XML_PUBMED}

    @override
    def convert(self) -> DoclingDocument:
        # Create empty document
        origin = DocumentOrigin(
            filename=self.file.name or "file",
            mimetype="application/xml",
            binary_hash=self.document_hash,
        )
        doc = DoclingDocument(name=self.file.stem or "file", origin=origin)

        _log.debug("Trying to convert PubMed XML document...")

        # Get parsed XML components
        xml_components: XMLComponents = self._parse()

        # Add XML components to the document
        doc = self._populate_document(doc, xml_components)
        return doc

    def _parse_title(self) -> str:
        title: str = " ".join(
            [
                t.replace("\n", "")
                for t in self.tree.xpath(".//title-group/article-title")[0].itertext()
            ]
        )
        return title

    def _parse_authors(self) -> list[Author]:
        # Get mapping between affiliation ids and names
        affiliation_names = []
        for affiliation_node in self.tree.xpath(".//aff[@id]"):
            affiliation_names.append(
                ": ".join([t for t in affiliation_node.itertext() if t != "\n"])
            )
        affiliation_ids_names = {
            id: name
            for id, name in zip(self.tree.xpath(".//aff[@id]/@id"), affiliation_names)
        }

        # Get author names and affiliation names
        authors: list[Author] = []
        for author_node in self.tree.xpath(
            './/contrib-group/contrib[@contrib-type="author"]'
        ):
            author: Author = {
                "name": "",
                "affiliation_names": [],
            }

            # Affiliation names
            affiliation_ids = [
                a.attrib["rid"] for a in author_node.xpath('xref[@ref-type="aff"]')
            ]
            for id in affiliation_ids:
                if id in affiliation_ids_names:
                    author["affiliation_names"].append(affiliation_ids_names[id])

            # Name
            author["name"] = (
                author_node.xpath("name/surname")[0].text
                + " "
                + author_node.xpath("name/given-names")[0].text
            )

            authors.append(author)
        return authors

    def _parse_abstract(self) -> str:
        texts = []
        for abstract_node in self.tree.xpath(".//abstract"):
            for text in abstract_node.itertext():
                texts.append(text.replace("\n", ""))
        abstract: str = "".join(texts)
        return abstract

    def _parse_main_text(self) -> list[Paragraph]:
        paragraphs: list[Paragraph] = []
        for paragraph_node in self.tree.xpath("//body//p"):
            # Skip captions
            if "/caption" in paragraph_node.getroottree().getpath(paragraph_node):
                continue

            paragraph: Paragraph = {"text": "", "headers": []}

            # Text
            paragraph["text"] = "".join(
                [t.replace("\n", "") for t in paragraph_node.itertext()]
            )

            # Header
            path = "../title"
            while len(paragraph_node.xpath(path)) > 0:
                paragraph["headers"].append(
                    "".join(
                        [
                            t.replace("\n", "")
                            for t in paragraph_node.xpath(path)[0].itertext()
                        ]
                    )
                )
                path = "../" + path

            paragraphs.append(paragraph)

        return paragraphs

    def _parse_tables(self) -> list[Table]:
        tables: list[Table] = []
        for table_node in self.tree.xpath(".//body//table-wrap"):
            table: Table = {"label": "", "caption": "", "content": ""}

            # Content
            if len(table_node.xpath("table")) > 0:
                table_content_node = table_node.xpath("table")[0]
            elif len(table_node.xpath("alternatives/table")) > 0:
                table_content_node = table_node.xpath("alternatives/table")[0]
            else:
                table_content_node = None
            if table_content_node != None:
                table["content"] = etree.tostring(table_content_node).decode("utf-8")

            # Caption
            if len(table_node.xpath("caption/p")) > 0:
                caption_node = table_node.xpath("caption/p")[0]
            elif len(table_node.xpath("caption/title")) > 0:
                caption_node = table_node.xpath("caption/title")[0]
            else:
                caption_node = None
            if caption_node != None:
                table["caption"] = "".join(
                    [t.replace("\n", "") for t in caption_node.itertext()]
                )

            # Label
            if len(table_node.xpath("label")) > 0:
                table["label"] = table_node.xpath("label")[0].text

            tables.append(table)
        return tables

    def _parse_figure_captions(self) -> list[FigureCaption]:
        figure_captions: list[FigureCaption] = []

        if not (self.tree.xpath(".//fig")):
            return figure_captions

        for figure_node in self.tree.xpath(".//fig"):
            figure_caption: FigureCaption = {
                "caption": "",
                "label": "",
            }

            # Label
            if figure_node.xpath("label"):
                figure_caption["label"] = "".join(
                    [
                        t.replace("\n", "")
                        for t in figure_node.xpath("label")[0].itertext()
                    ]
                )

            # Caption
            if figure_node.xpath("caption"):
                caption = ""
                for caption_node in figure_node.xpath("caption")[0].getchildren():
                    caption += (
                        "".join([t.replace("\n", "") for t in caption_node.itertext()])
                        + "\n"
                    )
                figure_caption["caption"] = caption

            figure_captions.append(figure_caption)

        return figure_captions

    def _parse_references(self) -> list[Reference]:
        references: list[Reference] = []
        for reference_node_abs in self.tree.xpath(".//ref-list/ref"):
            reference: Reference = {
                "author_names": "",
                "title": "",
                "journal": "",
                "year": "",
            }
            reference_node: Any = None
            for tag in ["mixed-citation", "element-citation", "citation"]:
                if len(reference_node_abs.xpath(tag)) > 0:
                    reference_node = reference_node_abs.xpath(tag)[0]
                    break

            if reference_node is None:
                continue

            if all(
                not (ref_type in ["citation-type", "publication-type"])
                for ref_type in reference_node.attrib.keys()
            ):
                continue

            # Author names
            names = []
            if len(reference_node.xpath("name")) > 0:
                for name_node in reference_node.xpath("name"):
                    name_str = " ".join(
                        [t.text for t in name_node.getchildren() if (t.text != None)]
                    )
                    names.append(name_str)
            elif len(reference_node.xpath("person-group")) > 0:
                for name_node in reference_node.xpath("person-group")[0]:
                    name_str = (
                        name_node.xpath("given-names")[0].text
                        + " "
                        + name_node.xpath("surname")[0].text
                    )
                    names.append(name_str)
            reference["author_names"] = "; ".join(names)

            # Title
            if len(reference_node.xpath("article-title")) > 0:
                reference["title"] = " ".join(
                    [
                        t.replace("\n", " ")
                        for t in reference_node.xpath("article-title")[0].itertext()
                    ]
                )

            # Journal
            if len(reference_node.xpath("source")) > 0:
                reference["journal"] = reference_node.xpath("source")[0].text

            # Year
            if len(reference_node.xpath("year")) > 0:
                reference["year"] = reference_node.xpath("year")[0].text

            if (
                not (reference_node.xpath("article-title"))
                and not (reference_node.xpath("journal"))
                and not (reference_node.xpath("year"))
            ):
                reference["title"] = reference_node.text

            references.append(reference)
        return references

    def _parse(self) -> XMLComponents:
        """Parsing PubMed document."""
        xml_components: XMLComponents = {
            "title": self._parse_title(),
            "authors": self._parse_authors(),
            "abstract": self._parse_abstract(),
            "paragraphs": self._parse_main_text(),
            "tables": self._parse_tables(),
            "figure_captions": self._parse_figure_captions(),
            "references": self._parse_references(),
        }
        return xml_components

    def _populate_document(
        self, doc: DoclingDocument, xml_components: XMLComponents
    ) -> DoclingDocument:
        self._add_title(doc, xml_components)
        self._add_authors(doc, xml_components)
        self._add_abstract(doc, xml_components)
        self._add_main_text(doc, xml_components)

        if xml_components["tables"]:
            self._add_tables(doc, xml_components)

        if xml_components["figure_captions"]:
            self._add_figure_captions(doc, xml_components)

        self._add_references(doc, xml_components)
        return doc

    def _add_figure_captions(
        self, doc: DoclingDocument, xml_components: XMLComponents
    ) -> None:
        self.parents["Figures"] = doc.add_heading(
            parent=self.parents["Title"], text="Figures"
        )
        for figure_caption_xml_component in xml_components["figure_captions"]:
            figure_caption_text = (
                figure_caption_xml_component["label"]
                + ": "
                + figure_caption_xml_component["caption"].strip()
            )
            fig_caption = doc.add_text(
                label=DocItemLabel.CAPTION, text=figure_caption_text
            )
            doc.add_picture(
                parent=self.parents["Figures"],
                caption=fig_caption,
            )
        return

    def _add_title(self, doc: DoclingDocument, xml_components: XMLComponents) -> None:
        self.parents["Title"] = doc.add_text(
            parent=None,
            text=xml_components["title"],
            label=DocItemLabel.TITLE,
        )
        return

    def _add_authors(self, doc: DoclingDocument, xml_components: XMLComponents) -> None:
        authors_affiliations: list = []
        for author in xml_components["authors"]:
            authors_affiliations.append(author["name"])
            authors_affiliations.append(", ".join(author["affiliation_names"]))
        authors_affiliations_str = "; ".join(authors_affiliations)

        doc.add_text(
            parent=self.parents["Title"],
            text=authors_affiliations_str,
            label=DocItemLabel.PARAGRAPH,
        )
        return

    def _add_abstract(
        self, doc: DoclingDocument, xml_components: XMLComponents
    ) -> None:
        abstract_text: str = xml_components["abstract"]
        self.parents["Abstract"] = doc.add_heading(
            parent=self.parents["Title"], text="Abstract"
        )
        doc.add_text(
            parent=self.parents["Abstract"],
            text=abstract_text,
            label=DocItemLabel.TEXT,
        )
        return

    def _add_main_text(
        self, doc: DoclingDocument, xml_components: XMLComponents
    ) -> None:
        added_headers: list = []
        for paragraph in xml_components["paragraphs"]:
            if not (paragraph["headers"]):
                continue

            # Header
            for i, header in enumerate(reversed(paragraph["headers"])):
                if header in added_headers:
                    continue
                added_headers.append(header)

                if ((i - 1) >= 0) and list(reversed(paragraph["headers"]))[
                    i - 1
                ] in self.parents:
                    parent = self.parents[list(reversed(paragraph["headers"]))[i - 1]]
                else:
                    parent = self.parents["Title"]

                self.parents[header] = doc.add_heading(parent=parent, text=header)

            # Paragraph text
            if paragraph["headers"][0] in self.parents:
                parent = self.parents[paragraph["headers"][0]]
            else:
                parent = self.parents["Title"]

            doc.add_text(parent=parent, label=DocItemLabel.TEXT, text=paragraph["text"])
        return

    def _add_references(
        self, doc: DoclingDocument, xml_components: XMLComponents
    ) -> None:
        self.parents["References"] = doc.add_heading(
            parent=self.parents["Title"], text="References"
        )
        current_list = doc.add_group(
            parent=self.parents["References"], label=GroupLabel.LIST, name="list"
        )
        for reference in xml_components["references"]:
            reference_text: str = ""
            if reference["author_names"]:
                reference_text += reference["author_names"] + ". "

            if reference["title"]:
                reference_text += reference["title"]
                if reference["title"][-1] != ".":
                    reference_text += "."
                reference_text += " "

            if reference["journal"]:
                reference_text += reference["journal"]

            if reference["year"]:
                reference_text += " (" + reference["year"] + ")"

            if not (reference_text):
                _log.debug(f"Skipping reference for: {str(self.file)}")
                continue

            doc.add_list_item(
                text=reference_text, enumerated=False, parent=current_list
            )
        return

    def _add_tables(self, doc: DoclingDocument, xml_components: XMLComponents) -> None:
        self.parents["Tables"] = doc.add_heading(
            parent=self.parents["Title"], text="Tables"
        )
        for table_xml_component in xml_components["tables"]:
            try:
                self._add_table(doc, table_xml_component)
            except Exception as e:
                _log.debug(f"Skipping unsupported table for: {str(self.file)}")
                pass
        return

    def _add_table(self, doc: DoclingDocument, table_xml_component: Table) -> None:
        soup = BeautifulSoup(table_xml_component["content"], "html.parser")
        table_tag = soup.find("table")

        nested_tables = table_tag.find("table")
        if nested_tables:
            _log.debug(f"Skipping nested table for: {str(self.file)}")
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

            # Extract and print the text content of each cell
            col_idx = 0
            for _, html_cell in enumerate(cells):
                text = html_cell.text

                col_span = int(html_cell.get("colspan", 1))
                row_span = int(html_cell.get("rowspan", 1))

                while grid[row_idx][col_idx] != None:
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
            text=table_xml_component["label"] + ": " + table_xml_component["caption"],
        )
        doc.add_table(data=data, parent=self.parents["Tables"], caption=table_caption)
        return
