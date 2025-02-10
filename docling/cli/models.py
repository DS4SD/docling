import logging
import warnings
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

from docling.datamodel.settings import settings
from docling.utils.model_downloader import download_models

warnings.filterwarnings(action="ignore", category=UserWarning, module="pydantic|torch")
warnings.filterwarnings(action="ignore", category=FutureWarning, module="easyocr")

console = Console()
err_console = Console(stderr=True)


app = typer.Typer(
    name="Docling models helper",
    no_args_is_help=True,
    add_completion=False,
    pretty_exceptions_enable=False,
)


class _AvailableModels(str, Enum):
    LAYOUT = "layout"
    TABLEFORMER = "tableformer"
    CODE_FORMULA = "code_formula"
    PICTURE_CLASSIFIER = "picture_classifier"
    SMOLVLM = "smolvlm"
    EASYOCR = "easyocr"


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
    ] = (settings.cache_dir / "models"),
    force: Annotated[
        bool, typer.Option(..., help="If true, the download will be forced")
    ] = False,
    models: Annotated[
        Optional[list[_AvailableModels]],
        typer.Argument(
            help=f"Models to download (default behavior: all will be downloaded)",
        ),
    ] = None,
    quiet: Annotated[
        bool,
        typer.Option(
            ...,
            "-q",
            "--quiet",
            help="No extra output is generated, the CLI prints only the directory with the cached models.",
        ),
    ] = False,
):
    if not quiet:
        FORMAT = "%(message)s"
        logging.basicConfig(
            level=logging.INFO,
            format="[blue]%(message)s[/blue]",
            datefmt="[%X]",
            handlers=[RichHandler(show_level=False, show_time=False, markup=True)],
        )
    to_download = models or [m for m in _AvailableModels]
    output_dir = download_models(
        output_dir=output_dir,
        force=force,
        progress=(not quiet),
        with_layout=_AvailableModels.LAYOUT in to_download,
        with_tableformer=_AvailableModels.TABLEFORMER in to_download,
        with_code_formula=_AvailableModels.CODE_FORMULA in to_download,
        with_picture_classifier=_AvailableModels.PICTURE_CLASSIFIER in to_download,
        with_smolvlm=_AvailableModels.SMOLVLM in to_download,
        with_easyocr=_AvailableModels.EASYOCR in to_download,
    )

    if quiet:
        typer.echo(output_dir)
    else:
        typer.secho(f"\nModels downloaded into: {output_dir}.", fg="green")

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
