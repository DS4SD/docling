import logging
from pathlib import Path
from typing import Optional

from docling.datamodel.settings import settings
from docling.models.code_formula_model import CodeFormulaModel
from docling.models.document_picture_classifier import DocumentPictureClassifier
from docling.models.easyocr_model import EasyOcrModel
from docling.models.layout_model import LayoutModel
from docling.models.rapid_ocr_model import RapidOcrModel
from docling.models.table_structure_model import TableStructureModel

_log = logging.getLogger(__name__)


def download_all(
    output_dir: Optional[Path] = None,
    *,
    force: bool = False,
    progress: bool = False,
    layout: bool = True,
    tableformer: bool = True,
    code_formula: bool = True,
    picture_classifier: bool = True,
    easyocr: bool = True,
    rapidocr: bool = True,
):
    if output_dir is None:
        output_dir = settings.cache_dir / "models"

    # Make sure the folder exists
    output_dir.mkdir(exist_ok=True, parents=True)

    if layout:
        _log.info(f"Downloading layout model...")
        LayoutModel.download_models(
            local_dir=output_dir / LayoutModel._model_repo_folder,
            force=force,
            progress=progress,
        )

    if tableformer:
        _log.info(f"Downloading tableformer model...")
        TableStructureModel.download_models(
            local_dir=output_dir / TableStructureModel._model_repo_folder,
            force=force,
            progress=progress,
        )

    if picture_classifier:
        _log.info(f"Downloading picture classifier model...")
        DocumentPictureClassifier.download_models(
            local_dir=output_dir / DocumentPictureClassifier._model_repo_folder,
            force=force,
            progress=progress,
        )

    if code_formula:
        _log.info(f"Downloading code formula model...")
        CodeFormulaModel.download_models(
            local_dir=output_dir / CodeFormulaModel._model_repo_folder,
            force=force,
            progress=progress,
        )

    if easyocr:
        _log.info(f"Downloading easyocr models...")
        EasyOcrModel.download_models(
            local_dir=output_dir / EasyOcrModel._model_repo_folder,
            force=force,
            progress=progress,
        )

    return output_dir
