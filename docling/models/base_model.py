import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Iterable, Type

from docling_core.types.doc import DoclingDocument, NodeItem

from docling.datamodel.base_models import Page
from docling.datamodel.document import ConversionResult, ProfilingItem, ProfilingScope
from docling.datamodel.settings import settings


class BasePageModel(ABC):
    @abstractmethod
    def __call__(
        self, conv_res: ConversionResult, page_batch: Iterable[Page]
    ) -> Iterable[Page]:
        pass


class BaseEnrichmentModel(ABC):

    @abstractmethod
    def is_processable(self, doc: DoclingDocument, element: NodeItem) -> bool:
        pass

    @abstractmethod
    def __call__(
        self, doc: DoclingDocument, element_batch: Iterable[NodeItem]
    ) -> Iterable[Any]:
        pass


class TimeRecorder:
    def __init__(
        self,
        conv_res: ConversionResult,
        key: str,
        scope: ProfilingScope = ProfilingScope.PAGE,
    ):
        if settings.debug.profile_pipeline_timings:
            if key not in conv_res.timings.keys():
                conv_res.timings[key] = ProfilingItem(scope=scope)
            self.conv_res = conv_res
            self.key = key

    def __enter__(self):
        if settings.debug.profile_pipeline_timings:
            self.start = time.monotonic()
        return self

    def __exit__(self, *args):
        if settings.debug.profile_pipeline_timings:
            elapsed = time.monotonic() - self.start
            self.conv_res.timings[self.key].times.append(elapsed)
            self.conv_res.timings[self.key].count += 1
