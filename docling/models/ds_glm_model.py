import copy
import random

from deepsearch_glm.nlp_utils import init_nlp_model
from deepsearch_glm.utils.doc_utils import to_legacy_document_format
from deepsearch_glm.utils.load_pretrained_models import load_pretrained_nlp_models
from docling_core.types import BaseText
from docling_core.types import Document as DsDocument
from docling_core.types import Ref
from PIL import ImageDraw

from docling.datamodel.base_models import BoundingBox, Cluster, CoordOrigin
from docling.datamodel.document import ConversionResult


class GlmModel:
    def __init__(self, config):
        self.config = config
        self.model_names = self.config.get(
            "model_names", ""
        )  # "language;term;reference"
        load_pretrained_nlp_models()
        # model = init_nlp_model(model_names="language;term;reference")
        model = init_nlp_model(model_names=self.model_names)
        self.model = model

    def __call__(self, conv_res: ConversionResult) -> DsDocument:
        ds_doc = conv_res._to_ds_document()
        ds_doc_dict = ds_doc.model_dump(by_alias=True)

        glm_doc = self.model.apply_on_doc(ds_doc_dict)
        ds_doc_dict = to_legacy_document_format(
            glm_doc, ds_doc_dict, update_name_label=True
        )

        exported_doc = DsDocument.model_validate(ds_doc_dict)

        # DEBUG code:
        def draw_clusters_and_cells(ds_document, page_no):
            clusters_to_draw = []
            image = copy.deepcopy(conv_res.pages[page_no].image)
            for ix, elem in enumerate(ds_document.main_text):
                if isinstance(elem, BaseText):
                    prov = elem.prov[0]
                elif isinstance(elem, Ref):
                    _, arr, index = elem.ref.split("/")
                    index = int(index)
                    if arr == "tables":
                        prov = ds_document.tables[index].prov[0]
                    elif arr == "figures":
                        prov = ds_document.figures[index].prov[0]
                    else:
                        prov = None

                if prov and prov.page == page_no:
                    clusters_to_draw.append(
                        Cluster(
                            id=ix,
                            label=elem.name,
                            bbox=BoundingBox.from_tuple(
                                coord=prov.bbox,
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
            image.show()

        # draw_clusters_and_cells(ds_doc, 0)
        # draw_clusters_and_cells(exported_doc, 0)

        return exported_doc
