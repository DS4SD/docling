import logging

import torch

from docling.datamodel.pipeline_options import AcceleratorDevice

_log = logging.getLogger(__name__)


def decide_device(accelerator_device: AcceleratorDevice) -> str:
    r"""
    Resolve the device based on the acceleration options and the available devices in the system
    Rules:
    1. AUTO: Check for the best available device on the system.
    2. User-defined: Check if the device actually exists, otherwise fall-back to CPU
    """
    cuda_index = 0
    device = "cpu"

    has_cuda = torch.backends.cuda.is_built() and torch.cuda.is_available()
    has_mps = torch.backends.mps.is_built() and torch.backends.mps.is_available()

    if accelerator_device == AcceleratorDevice.AUTO:
        if has_cuda:
            device = f"cuda:{cuda_index}"
        elif has_mps:
            device = "mps"

    else:
        if accelerator_device == AcceleratorDevice.CUDA:
            if has_cuda:
                device = f"cuda:{cuda_index}"
            else:
                _log.warning("CUDA is not available in the system. Fall back to 'CPU'")
        elif accelerator_device == AcceleratorDevice.MPS:
            if has_mps:
                device = "mps"
            else:
                _log.warning("MPS is not available in the system. Fall back to 'CPU'")

    _log.info("Accelerator device: '%s'", device)
    return device
