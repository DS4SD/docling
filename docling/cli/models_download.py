import logging
import warnings
from pathlib import Path
from typing import Annotated

import typer

from docling.datamodel.settings import settings
from docling.models.code_formula_model import CodeFormulaModel
from docling.models.document_picture_classifier import DocumentPictureClassifier
from docling.models.easyocr_model import EasyOcrModel
from docling.models.layout_model import LayoutModel
from docling.models.rapid_ocr_model import RapidOcrModel
from docling.models.table_structure_model import TableStructureModel
from docling.utils.models_downloader import download_all

warnings.filterwarnings(action="ignore", category=UserWarning, module="pydantic|torch")
warnings.filterwarnings(action="ignore", category=FutureWarning, module="easyocr")

_log = logging.getLogger(__name__)
from rich.console import Console
from rich.logging import RichHandler

console = Console()
err_console = Console(stderr=True)


app = typer.Typer(
    name="Docling models helper",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)


@app.command("download")
def download(
    output_dir: Annotated[
        Path,
        typer.Option(
            ...,
            "-o",
            "--output-dir",
            help="The directory where all the models are downloaded.",
        ),
    ] = settings.cache_dir
    / "models",
    force: Annotated[
        bool, typer.Option(..., help="If true, the download will be forced")
    ] = False,
    quite: Annotated[
        bool,
        typer.Option(
            ...,
            "-q",
            help="No extra output is generated, the CLI print only the directory with the cached models.",
        ),
    ] = False,
    layout: Annotated[
        bool,
        typer.Option(..., help="If true, the layout model weights are downloaded."),
    ] = True,
    tableformer: Annotated[
        bool,
        typer.Option(
            ..., help="If true, the tableformer model weights are downloaded."
        ),
    ] = True,
    code_formula: Annotated[
        bool,
        typer.Option(
            ..., help="If true, the code formula model weights are downloaded."
        ),
    ] = True,
    picture_classifier: Annotated[
        bool,
        typer.Option(
            ..., help="If true, the picture classifier model weights are downloaded."
        ),
    ] = True,
    easyocr: Annotated[
        bool,
        typer.Option(..., help="If true, the easyocr model weights are downloaded."),
    ] = True,
    rapidocr: Annotated[
        bool,
        typer.Option(..., help="If true, the rapidocr model weights are downloaded."),
    ] = True,
):
    if not quite:
        FORMAT = "%(message)s"
        logging.basicConfig(
            level=logging.INFO,
            format="[blue]%(message)s[/blue]",
            datefmt="[%X]",
            handlers=[RichHandler(show_level=False, show_time=False, markup=True)],
        )

    output_dir = download_all(
        output_dir=output_dir,
        force=force,
        progress=(not quite),
        layout=layout,
        tableformer=tableformer,
        code_formula=code_formula,
        picture_classifier=picture_classifier,
        easyocr=easyocr,
        rapidocr=rapidocr,
    )

    if quite:
        typer.echo(output_dir)
    else:
        typer.secho(
            f"\nAll models downloaded in the directory {output_dir}.", fg="green"
        )

        console.print(
            "\n",
            "Docling can now be configured for running offline using the local artifacts.\n\n",
            "Using the CLI:",
            f"`docling --artifacts-path={output_dir} FILE`",
            "\n",
            "Using Python: see the documentation at <https://ds4sd.github.io/docling/usage>.",
        )


click_app = typer.main.get_command(app)

if __name__ == "__main__":
    app()
