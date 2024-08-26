import glob

from pathlib import Path

from docling.backend.docling_parse_backend import DoclingParseDocumentBackend
from docling.datamodel.base_models import ConversionStatus, PipelineOptions
from docling.document_converter import DocumentConverter

GENERATE=True

def get_pdf_paths():

    # Define the directory you want to search
    directory = Path('./data')

    # List all PDF files in the directory and its subdirectories
    pdf_files = sorted(directory.rglob('*.pdf'))
    return pdf_files

def verify_json(doc_pred_json, doc_true_json):
    return True

def verify_md(doc_pred_md, doc_true_md):
    return (doc_pred_md==doc_true_md)
    
def test_conversions():
    
    pdf_paths = get_pdf_paths()

    pipeline_options = PipelineOptions()
    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True

    doc_converter = DocumentConverter(
        pipeline_options=pipeline_options,
        pdf_backend=DoclingParseDocumentBackend,
    )
    
    for path in pdf_paths:

        doc_pred_json = converter.convert_single(path)        
        
        doc_pred_md = doc.render_as_markdown()

        json_path = path.with_suffix(".json")
        md_path = path.with_suffix(".md")
            
        if GENERATE:
            
            with open(json_path, "w") as fw:
                fw.write(json.dumps(doc_pred_json, indent=2))

            with open(md_path, "w") as fw:
                fw.write(doc_pred_md)
                
        else:

            with open(path, "r") as fr:
                doc_true_json = json.load(fr)

            with open(path, "r") as fr:
                doc_true_md = json.load(fr)        

            assert verify_json(doc_pred_json, doc_true_json), f"failed json prediction for {path}"

            assert verify_md(doc_pred_md, doc_true_md), f"failed md prediction for {path}"
        
