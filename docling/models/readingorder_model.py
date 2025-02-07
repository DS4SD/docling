import copy
import random
from pathlib import Path
from typing import Dict, List

from docling_core.types.doc import (
    BoundingBox,
    CoordOrigin,
    DocItemLabel,
    DoclingDocument,
    DocumentOrigin,
    GroupLabel,
    ProvenanceItem,
    RefItem,
    TableData,
)
from docling_core.types.legacy_doc.base import Ref
from docling_core.types.legacy_doc.document import BaseText
from docling_ibm_models.reading_order.reading_order_rb import (
    PageElement as ReadingOrderPageElement,
)
from docling_ibm_models.reading_order.reading_order_rb import ReadingOrderPredictor
from PIL import ImageDraw
from pydantic import BaseModel, ConfigDict

from docling.datamodel.base_models import (
    Cluster,
    ContainerElement,
    FigureElement,
    Table,
    TextElement,
)
from docling.datamodel.document import ConversionResult
from docling.datamodel.settings import settings
from docling.utils.profiling import ProfilingScope, TimeRecorder


class ReadingOrderOptions(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    model_names: str = ""  # e.g. "language;term;reference"


class ReadingOrderModel:
    def __init__(self, options: ReadingOrderOptions):
        self.options = options
        self.ro_model = ReadingOrderPredictor()

    def _assembled_to_readingorder_elements(
        self, conv_res: ConversionResult
    ) -> List[ReadingOrderPageElement]:

        elements: List[ReadingOrderPageElement] = []

        for (
            element
        ) in (
            conv_res.assembled.body
        ):  # FIXME: use conv_res.assembled.elements (include furniture)

            page_height = conv_res.pages[element.page_no].size.height  # type: ignore
            bbox = element.cluster.bbox.to_bottom_left_origin(page_height)
            text = element.text or ""

            elements.append(
                ReadingOrderPageElement(
                    cid=len(elements),
                    ref=RefItem(cref=f"#/{element.page_no}/{element.cluster.id}"),
                    text=text,
                    page_no=element.page_no,
                    page_size=conv_res.pages[element.page_no].size,
                    label=element.label,
                    l=bbox.l,
                    r=bbox.r,
                    b=bbox.b,
                    t=bbox.t,
                    coord_origin=bbox.coord_origin,
                )
            )

        return elements

    def _readingorder_elements_to_docling_doc(
        self,
        conv_res: ConversionResult,
        ro_elements: List[ReadingOrderPageElement],
        el_to_captions_mapping: Dict[int, List[int]],
        el_to_footnotes_mapping: Dict[int, List[int]],
        el_merges_mapping: Dict[int, List[int]],
    ) -> DoclingDocument:

        id_to_elem = {
            RefItem(cref=f"#/{elem.page_no}/{elem.cluster.id}").cref: elem
            for elem in conv_res.assembled.elements
        }

        origin = DocumentOrigin(
            mimetype="application/pdf",
            filename=conv_res.input.file.name,
            binary_hash=conv_res.input.document_hash,
        )
        doc_name = Path(origin.filename).stem
        out_doc: DoclingDocument = DoclingDocument(name=doc_name, origin=origin)

        for page in conv_res.pages:
            page_no = page.page_no + 1
            size = page.size

            assert size is not None

            out_doc.add_page(page_no=page_no, size=size)

        current_list = None

        # TODO: handle merges

        for rel in ro_elements:
            element = id_to_elem[rel.ref.cref]

            page_height = conv_res.pages[element.page_no].size.height  # type: ignore

            if isinstance(element, TextElement):
                text = element.text

                prov = ProvenanceItem(
                    page_no=element.page_no + 1,
                    charspan=(0, len(text)),
                    bbox=element.cluster.bbox.to_bottom_left_origin(page_height),
                )
                label = element.label

                if label == DocItemLabel.LIST_ITEM:
                    if current_list is None:
                        current_list = out_doc.add_group(
                            label=GroupLabel.LIST, name="list"
                        )

                    # TODO: Infer if this is a numbered or a bullet list item
                    out_doc.add_list_item(
                        text=text, enumerated=False, prov=prov, parent=current_list
                    )
                elif label == DocItemLabel.SECTION_HEADER:
                    current_list = None

                    out_doc.add_heading(text=text, prov=prov)
                elif label == DocItemLabel.CODE:
                    current_list = None

                    out_doc.add_code(text=text, prov=prov)
                elif label == DocItemLabel.FORMULA:
                    current_list = None

                    out_doc.add_text(
                        label=DocItemLabel.FORMULA, text="", orig=text, prov=prov
                    )
                else:
                    current_list = None

                    out_doc.add_text(label=element.label, text=text, prov=prov)

            elif isinstance(element, Table):

                tbl_data = TableData(
                    num_rows=element.num_rows,
                    num_cols=element.num_cols,
                    table_cells=element.table_cells,
                )

                prov = ProvenanceItem(
                    page_no=element.page_no + 1,
                    charspan=(0, 0),
                    bbox=element.cluster.bbox.to_bottom_left_origin(page_height),
                )

                tbl = out_doc.add_table(
                    data=tbl_data, prov=prov, label=element.cluster.label
                )

                # TODO: handle element.cluster.children.
                # TODO: handle captions
                # tbl.captions.extend(caption_refs)

            elif isinstance(element, FigureElement):
                text = ""
                prov = ProvenanceItem(
                    page_no=element.page_no + 1,
                    charspan=(0, len(text)),
                    bbox=element.cluster.bbox.to_bottom_left_origin(page_height),
                )

                pic = out_doc.add_picture(prov=prov)

                # TODO: handle element.cluster.children.
                # TODO: handle captions
                # pic.captions.extend(caption_refs)
                # _add_child_elements(pic, doc, obj, pelem)

            elif isinstance(element, ContainerElement):
                pass
                # TODO: handle element.cluster.children.

        return out_doc

    def __call__(self, conv_res: ConversionResult) -> DoclingDocument:
        with TimeRecorder(conv_res, "glm", scope=ProfilingScope.DOCUMENT):
            page_elements = self._assembled_to_readingorder_elements(conv_res)

            # Apply reading order
            sorted_elements = self.ro_model.predict_reading_order(
                page_elements=page_elements
            )
            el_to_captions_mapping = self.ro_model.predict_to_captions(
                sorted_elements=sorted_elements
            )
            el_to_footnotes_mapping = self.ro_model.predict_to_footnotes(
                sorted_elements=sorted_elements
            )
            el_merges_mapping = self.ro_model.predict_merges(
                sorted_elements=sorted_elements
            )

            docling_doc: DoclingDocument = self._readingorder_elements_to_docling_doc(
                conv_res,
                sorted_elements,
                el_to_captions_mapping,
                el_to_footnotes_mapping,
                el_merges_mapping,
            )

        # DEBUG code:
        def draw_clusters_and_cells(ds_document, page_no, show: bool = False):
            clusters_to_draw = []
            image = copy.deepcopy(conv_res.pages[page_no].image)
            for ix, elem in enumerate(ds_document.main_text):
                if isinstance(elem, BaseText):
                    prov = elem.prov[0]  # type: ignore
                elif isinstance(elem, Ref):
                    _, arr, index = elem.ref.split("/")
                    index = int(index)  # type: ignore
                    if arr == "tables":
                        prov = ds_document.tables[index].prov[0]
                    elif arr == "figures":
                        prov = ds_document.pictures[index].prov[0]
                    else:
                        prov = None

                if prov and prov.page == page_no:
                    clusters_to_draw.append(
                        Cluster(
                            id=ix,
                            label=elem.name,
                            bbox=BoundingBox.from_tuple(
                                coord=prov.bbox,  # type: ignore
                                origin=CoordOrigin.BOTTOMLEFT,
                            ).to_top_left_origin(conv_res.pages[page_no].size.height),
                        )
                    )

            draw = ImageDraw.Draw(image)
            for c in clusters_to_draw:
                x0, y0, x1, y1 = c.bbox.as_tuple()
                draw.rectangle([(x0, y0), (x1, y1)], outline="red")
                draw.text((x0 + 2, y0 + 2), f"{c.id}:{c.label}", fill=(255, 0, 0, 255))

                cell_color = (
                    random.randint(30, 140),
                    random.randint(30, 140),
                    random.randint(30, 140),
                )
                for tc in c.cells:  # [:1]:
                    x0, y0, x1, y1 = tc.bbox.as_tuple()
                    draw.rectangle([(x0, y0), (x1, y1)], outline=cell_color)

            if show:
                image.show()
            else:
                out_path: Path = (
                    Path(settings.debug.debug_output_path)
                    / f"debug_{conv_res.input.file.stem}"
                )
                out_path.mkdir(parents=True, exist_ok=True)

                out_file = out_path / f"doc_page_{page_no:05}.png"
                image.save(str(out_file), format="png")

        # for item in ds_doc.page_dimensions:
        #    page_no = item.page
        #    draw_clusters_and_cells(ds_doc, page_no)

        return docling_doc
