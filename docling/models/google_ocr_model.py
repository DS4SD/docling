import io
import logging
from typing import Iterable

from docling_core.types.doc import BoundingBox, CoordOrigin

from docling.datamodel.base_models import Cell, OcrCell, Page
from docling.datamodel.document import ConversionResult
from docling.datamodel.pipeline_options import GoogleOcrOptions
from docling.datamodel.settings import settings
from docling.models.base_ocr_model import BaseOcrModel
from docling.utils.profiling import TimeRecorder

_log = logging.getLogger(__name__)


class GoogleOcrModel(BaseOcrModel):
    def __init__(self, enabled: bool, options: GoogleOcrOptions):
        super().__init__(enabled=enabled, options=options)
        self.options: GoogleOcrOptions

        self.scale = 3  # multiplier for 72 dpi == 216 dpi.
        self.reader = None

        if self.enabled:
            try:
                from google.cloud import vision
                from google.oauth2 import service_account

                # Initialize the tesseractAPI
                _log.debug("Initializing Google OCR ")
                self.image_context = {"language_hints": self.options.lang}
                client_options = {"api_endpoint": self.options.google_ocr_region}
                if self.options.google_ocr_config_file_path is None:
                    raise FileNotFoundError(
                        "Google OCR Config File is missing. Please provide a valid file path "
                        "via the GOOGLE_CONFIG_FILE_PATH environment variable."
                    )
                google_creds = service_account.Credentials.from_service_account_file(
                    self.options.google_ocr_config_file_path
                )
                self.reader = vision.ImageAnnotatorClient(
                    credentials=google_creds, client_options=client_options
                )

            except ImportError:
                raise ImportError(
                    "Failed to import required libraries for Google OCR. Ensure that the "
                    "'google-cloud-vision' and 'google-auth' packages are installed. "
                    "You can install them using 'pip install google-cloud-vision google-auth'."
                )

    def __del__(self):
        if self.reader is not None:
            pass

    def __call__(
        self, conv_res: ConversionResult, page_batch: Iterable[Page]
    ) -> Iterable[Page]:

        if not self.enabled:
            yield from page_batch
            return

        for page in page_batch:

            assert page._backend is not None
            if not page._backend.is_valid():
                yield page
            else:
                with TimeRecorder(conv_res, "ocr"):

                    assert self.reader is not None

                    ocr_rects = self.get_ocr_rects(page)
                    try:
                        all_ocr_cells = []
                        for ocr_rect in ocr_rects:
                            # Skip zero area boxes
                            if ocr_rect.area() == 0:
                                continue
                            high_res_image = page._backend.get_page_image(
                                scale=self.scale, cropbox=ocr_rect
                            )
                            # Convert Pillow image to content, represented as a stream of bytes, using IO buffer.
                            buffer = io.BytesIO()
                            try:
                                from google.cloud import vision
                                from google.oauth2 import service_account
                            except:
                                raise Exception

                            high_res_image.save(buffer, "PNG")
                            content = buffer.getvalue()

                            new_image = vision.Image(content=content)
                            google_response = self.reader.text_detection(
                                image=new_image, image_context=self.image_context
                            )

                            cells = []
                            ix = 0
                            for file_page in google_response.full_text_annotation.pages:
                                for block in file_page.blocks:
                                    for paragraph in block.paragraphs:
                                        for word in paragraph.words:
                                            box = word.bounding_box.vertices
                                            text = ""
                                            for symbol in word.symbols:
                                                text += symbol.text

                                            # Extract text within the bounding box
                                            confidence = word.confidence * 100
                                            left = (
                                                min(
                                                    box[0].x,
                                                    box[1].x,
                                                    box[2].x,
                                                    box[3].x,
                                                )
                                                / self.scale
                                            ) + ocr_rect.l
                                            bottom = (
                                                max(
                                                    box[0].y,
                                                    box[1].y,
                                                    box[2].y,
                                                    box[3].y,
                                                )
                                                / self.scale
                                            ) + ocr_rect.t
                                            top = (
                                                min(
                                                    box[0].y,
                                                    box[1].y,
                                                    box[2].y,
                                                    box[3].y,
                                                )
                                                / self.scale
                                            ) + ocr_rect.t
                                            right = (
                                                max(
                                                    box[0].x,
                                                    box[1].x,
                                                    box[2].x,
                                                    box[3].x,
                                                )
                                                / self.scale
                                            ) + ocr_rect.l

                                            cells.append(
                                                OcrCell(
                                                    id=ix,
                                                    text=text,
                                                    confidence=confidence,
                                                    bbox=BoundingBox.from_tuple(
                                                        coord=(
                                                            left,
                                                            top,
                                                            right,
                                                            bottom,
                                                        ),
                                                        origin=CoordOrigin.TOPLEFT,
                                                    ),
                                                )
                                            )
                                            ix += 1

                            del high_res_image, buffer, content
                            all_ocr_cells.extend(cells)
                    except Exception as e:
                        raise e
                    # Post-process the cells
                    page.cells = self.post_process_cells(all_ocr_cells, page.cells)

                # DEBUG code:
                if settings.debug.visualize_ocr:
                    self.draw_ocr_rects_and_cells(conv_res, page, ocr_rects, show=True)

                yield page
