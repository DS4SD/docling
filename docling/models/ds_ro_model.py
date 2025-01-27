
from typing import List, Dict
from pydantic import BaseModel, ConfigDict, TypeAdapter
from docling_ibm_models.reading_order.reading_order_rb import PageElement, ReadingOrderPredictor

class ReadingOrderRbOptions(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

class ReadingOrderRbModel:
    
    def __init__(self, options: ReadingOrderRbOptions):
        self.options = options

        self.model = ReadingOrderPredictor()        

    def __call__(self, conv_res: ConversionResult) -> DoclingDocument:

        with TimeRecorder(conv_res, "ReadingOrderRbModel", scope=ProfilingScope.DOCUMENT):

            pred_elements: Dict[int, List[PageElement]] = {}

            for element in conv_res.assembled.elements:

                page_no = element.page_no
                page_height = page_no_to_page[element.page_no].size.height
                
                bbox = element.cluster.bbox.to_bottom_left_origin(
                    page_height=page_height
                )

                if page_no not in pred_elements:
                    pred_elements[page_no] = []                

                    pred_elements[prov.page_no].append(
                        PageElement(
                            page_no=page_no,
                            cid=len(true_elements[page_no]),
                            pid=0,
                            label=element.label,
                            bbox=bbox
                        )
                    )                        

            for page_no,elements in pred_elements.items():                    
                sorted_elements, to_captions, to_footnotes = self.model.predict_page(page_elements=elements)
