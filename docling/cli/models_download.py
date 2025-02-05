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

warnings.filterwarnings(action="ignore", category=UserWarning, module="pydantic|torch")
warnings.filterwarnings(action="ignore", category=FutureWarning, module="easyocr")

_log = logging.getLogger(__name__)
from rich.console import Console

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
    # Make sure the folder exists
    output_dir.mkdir(exist_ok=True, parents=True)

    show_progress = not quite

    if layout:
        if not quite:
            typer.secho(f"Downloading layout model...", fg="blue")
        LayoutModel.download_models_hf(
            local_dir=output_dir / LayoutModel._model_repo_folder,
            force=force,
            progress=show_progress,
        )

    if tableformer:
        if not quite:
            typer.secho(f"Downloading tableformer model...", fg="blue")
        TableStructureModel.download_models_hf(
            local_dir=output_dir / TableStructureModel._model_repo_folder,
            force=force,
            progress=show_progress,
        )

    if picture_classifier:
        if not quite:
            typer.secho(f"Downloading picture classifier model...", fg="blue")
        DocumentPictureClassifier.download_models_hf(
            local_dir=output_dir / DocumentPictureClassifier._model_repo_folder,
            force=force,
            progress=show_progress,
        )

    if code_formula:
        if not quite:
            typer.secho(f"Downloading code formula model...", fg="blue")
        CodeFormulaModel.download_models_hf(
            local_dir=output_dir / CodeFormulaModel._model_repo_folder,
            force=force,
            progress=show_progress,
        )

    if easyocr:
        if not quite:
            typer.secho(f"Downloading easyocr models...", fg="blue")
        EasyOcrModel.download_models(
            local_dir=output_dir / EasyOcrModel._model_repo_folder,
            force=force,
            progress=show_progress,
        )

    if quite:
        typer.echo(output_dir)
    else:
        typer.secho(f"All models downloaded in the directory {output_dir}.", fg="green")

        console.print(
            "\n",
            "Docling can now be configured for running offline using the local artifacts.\n\n",
            "Using the CLI:",
            f"`docling --artifacts-path={output_dir} FILE`",
            "\n",
            "Using Python: see the documentation at <https://ds4sd.github.io/docling/usage>.",
        )


# @app.command(hidden=True)
# def other():
#     raise NotImplementedError()


click_app = typer.main.get_command(app)

if __name__ == "__main__":
    app()
