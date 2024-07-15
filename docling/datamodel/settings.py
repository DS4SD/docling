import sys

from pydantic import BaseModel
from pydantic_settings import BaseSettings


class DocumentLimits(BaseModel):
    max_num_pages: int = sys.maxsize
    max_file_size: int = sys.maxsize


class BatchConcurrencySettings(BaseModel):
    doc_batch_size: int = 2
    doc_batch_concurrency: int = 2
    page_batch_size: int = 4
    page_batch_concurrency: int = 2

    # doc_batch_size: int = 1
    # doc_batch_concurrency: int = 1
    # page_batch_size: int = 1
    # page_batch_concurrency: int = 1

    # model_concurrency: int = 2

    # To force models into single core: export OMP_NUM_THREADS=1


class AppSettings(BaseSettings):
    perf: BatchConcurrencySettings


settings = AppSettings(perf=BatchConcurrencySettings())
