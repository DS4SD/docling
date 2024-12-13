import sys
from pathlib import Path

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class DocumentLimits(BaseModel):
    max_num_pages: int = sys.maxsize
    max_file_size: int = sys.maxsize


class BatchConcurrencySettings(BaseModel):
    doc_batch_size: int = 2
    doc_batch_concurrency: int = 2
    page_batch_size: int = 4
    page_batch_concurrency: int = 2
    elements_batch_size: int = 16

    # doc_batch_size: int = 1
    # doc_batch_concurrency: int = 1
    # page_batch_size: int = 1
    # page_batch_concurrency: int = 1

    # model_concurrency: int = 2

    # To force models into single core: export OMP_NUM_THREADS=1


class DebugSettings(BaseModel):
    visualize_cells: bool = False
    visualize_ocr: bool = False
    visualize_layout: bool = False
    visualize_tables: bool = False

    profile_pipeline_timings: bool = False

    # Path used to output debug information.
    debug_output_path: str = str(Path.cwd() / "debug")


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DOCLING_", env_nested_delimiter="_")

    perf: BatchConcurrencySettings
    debug: DebugSettings


settings = AppSettings(perf=BatchConcurrencySettings(), debug=DebugSettings())
